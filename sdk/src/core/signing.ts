/**
 * Request signing — session-bound ECDSA (strategy step 3: "sign + nonce +
 * timestamp the payload... stop replay of a known-good vector").
 *
 * The site API key is public (it ships in browser JS on every customer's
 * page), and any symmetric secret delivered to JavaScript is retrievable by
 * the client. The browser therefore creates a non-exportable ECDSA P-256
 * private key and registers only the public JWK with the backend. Every
 * /api/predict call is signed with the private CryptoKey plus a nonce and
 * timestamp the server checks for freshness and single use.
 *
 * Uses the Web Crypto API (crypto.subtle), which requires a secure context
 * (HTTPS or localhost). If unavailable, signing is skipped entirely and the
 * request is sent unsigned — the backend's soft-enforcement mode accepts
 * that (see request_signing.py's REQUEST_SIGNING_MODE), so an unsupported
 * environment degrades gracefully in backend soft-enforcement mode.
 */

export interface SignedEnvelope {
  nonce: string;
  timestamp: number;
  signature: string;
}

function hasSubtleCrypto(): boolean {
  return typeof crypto !== 'undefined' && !!crypto.subtle && typeof crypto.subtle.generateKey === 'function';
}

const KEY_DB = 'veilproof-signing';
const KEY_STORE = 'session-keys';
const keyPairPromises = new Map<string, Promise<CryptoKeyPair | null>>();

function hexEncode(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer), (b) => b.toString(16).padStart(2, '0')).join('');
}

function openKeyDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === 'undefined') return Promise.resolve(null);
  return new Promise((resolve) => {
    try {
      const request = indexedDB.open(KEY_DB, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(KEY_STORE)) {
          request.result.createObjectStore(KEY_STORE);
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function loadStoredKeyPair(sessionId: string): Promise<CryptoKeyPair | null> {
  const db = await openKeyDb();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const transaction = db.transaction(KEY_STORE, 'readonly');
      const request = transaction.objectStore(KEY_STORE).get(sessionId);
      request.onsuccess = () => {
        const pair = request.result as CryptoKeyPair | undefined;
        resolve(pair?.privateKey && pair?.publicKey ? pair : null);
      };
      request.onerror = () => resolve(null);
      transaction.oncomplete = () => db.close();
      transaction.onerror = () => db.close();
    } catch {
      db.close();
      resolve(null);
    }
  });
}

async function storeKeyPair(sessionId: string, pair: CryptoKeyPair): Promise<void> {
  const db = await openKeyDb();
  if (!db) return;
  await new Promise<void>((resolve) => {
    try {
      const transaction = db.transaction(KEY_STORE, 'readwrite');
      transaction.objectStore(KEY_STORE).put(pair, sessionId);
      transaction.oncomplete = () => {
        db.close();
        resolve();
      };
      transaction.onerror = () => {
        db.close();
        resolve();
      };
    } catch {
      db.close();
      resolve();
    }
  });
}

async function getKeyPair(sessionId: string): Promise<CryptoKeyPair | null> {
  if (!hasSubtleCrypto()) return null;
  let promise = keyPairPromises.get(sessionId);
  if (!promise) {
    promise = (async () => {
      const stored = await loadStoredKeyPair(sessionId);
      if (stored) return stored;
      try {
        const pair = await crypto.subtle.generateKey(
          { name: 'ECDSA', namedCurve: 'P-256' },
          false, // private key non-exportable; public key remains exportable
          ['sign', 'verify']
        );
        await storeKeyPair(sessionId, pair);
        return pair;
      } catch {
        return null;
      }
    })();
    keyPairPromises.set(sessionId, promise);
  }
  return promise;
}

/** Public key registered with /api/signing/register. The private key never
 * leaves the browser's non-exportable CryptoKey. */
export async function getSigningPublicKey(sessionId: string): Promise<JsonWebKey | null> {
  const pair = await getKeyPair(sessionId);
  if (!pair) return null;
  try {
    return await crypto.subtle.exportKey('jwk', pair.publicKey);
  } catch {
    return null;
  }
}

/** 32 hex chars (128 bits) of cryptographic randomness, unique per request. */
export function generateNonce(): string | null {
  if (typeof crypto === 'undefined' || typeof crypto.getRandomValues !== 'function') {
    return null;
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Sign `bodyString` — the exact string about to be sent as the HTTP request
 * body — with the browser's non-exportable per-session private key. Signing
 * the literal outgoing string (rather than
 * re-deriving a "canonical" form on each side) avoids any risk of a
 * cross-language JSON re-serialization mismatch, the same approach webhook
 * signature schemes (Stripe/GitHub/Slack) use.
 *
 * Returns null if Web Crypto is unavailable, no secret is available, or
 * signing fails for any reason — callers must treat null as "send
 * unsigned," never as an error that should block getting a decision.
 */
export async function signRequest(
  sessionId: string,
  bodyString: string
): Promise<SignedEnvelope | null> {
  const pair = await getKeyPair(sessionId);
  const nonce = generateNonce();
  if (!pair || !nonce) return null;

  try {
    const timestamp = Date.now();
    const message = new TextEncoder().encode(`${sessionId}.${timestamp}.${nonce}.${bodyString}`);
    const digest = await crypto.subtle.sign(
      { name: 'ECDSA', hash: 'SHA-256' },
      pair.privateKey,
      message
    );
    return { nonce, timestamp, signature: hexEncode(digest) };
  } catch {
    return null;
  }
}
