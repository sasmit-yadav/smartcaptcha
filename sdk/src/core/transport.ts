/**
 * Transport Layer — sends telemetry batches to the backend API.
 * Uses fetch with keepalive for unload safety.
 * Retries on 5xx with exponential backoff.
 */

import { getSessionId, getSessionMeta } from './session.js';
import type { TelemetryEvent } from '../types.js';

let endpoint = '';
let apiKey = '';
let debug = false;
let retryCount = 0;
const MAX_RETRIES = 3;

let signingExpiresAt = 0;
let signingRegistration: Promise<boolean> | null = null;

export function initTransport(config: { endpoint: string; apiKey: string; debug?: boolean }): void {
  endpoint = config.endpoint;
  apiKey = config.apiKey;
  debug = config.debug || false;
  signingExpiresAt = 0;
  signingRegistration = null;
}

/** Register the SDK's browser-generated public key and keep the registration
 * fresh. Concurrent callers share one request, so getDecision() can safely
 * await this even when init() has already started registration. */
export async function registerSigningKey(
  sessionId: string,
  publicKey: JsonWebKey,
  force = false
): Promise<boolean> {
  const now = Date.now();
  if (!force && signingExpiresAt > now + 30_000) return true;
  if (!force && signingRegistration) return signingRegistration;

  signingRegistration = (async () => {
    try {
      const res = await fetch(`${endpoint}/api/signing/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ sessionId, publicKey }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok || !body?.registered || typeof body.expiresAt !== 'number') {
        if (debug && body?.enabled !== false) {
          console.warn('[VeilProof] Signing-key registration failed:', body?.detail || res.status);
        }
        signingExpiresAt = 0;
        return false;
      }
      signingExpiresAt = body.expiresAt;
      return true;
    } catch (err) {
      signingExpiresAt = 0;
      if (debug) console.warn('[VeilProof] Signing-key registration failed:', (err as Error).message);
      return false;
    } finally {
      signingRegistration = null;
    }
  })();
  return signingRegistration;
}

/**
 * Send a batch of events to the backend.
 */
export async function sendBatch(events: TelemetryEvent[]): Promise<void> {
  if (!endpoint) {
    if (debug) console.warn('[VeilProof] No endpoint configured, dropping batch');
    return;
  }

  const payload = {
    sessionId: getSessionId(),
    meta: getSessionMeta(),
    events,
    timestamp: Date.now(),
  };

  try {
    const res = await fetch(`${endpoint}/api/telemetry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify(payload),
      keepalive: true, // survives page close
    });

    if (res.ok) {
      retryCount = 0;
      if (debug) console.log(`[VeilProof] Batch sent: ${events.length} events queued`);
      return;
    }

    if (res.status === 429) {
      // Rate limited — back off
      if (debug) console.warn('[VeilProof] Rate limited (429), backing off');
      await delay(2000);
      retrySend(payload);
      return;
    }

    if (res.status >= 500) {
      // Server error — retry
      if (debug) console.warn(`[VeilProof] Server error ${res.status}, retrying`);
      retrySend(payload);
      return;
    }

    if (res.status >= 400) {
      // Client error — don't retry
      // Suppress 404 errors for lightweight backends that don't have telemetry endpoints
      if (res.status !== 404 && debug) {
        console.error(`[VeilProof] Client error ${res.status}, not retrying`);
      }
    }
  } catch (err) {
    if (debug) console.error('[VeilProof] Network error:', (err as Error).message);
    retrySend(payload);
  }
}

async function retrySend(payload: unknown): Promise<void> {
  if (retryCount >= MAX_RETRIES) {
    if (debug) console.warn('[VeilProof] Max retries reached, dropping batch');
    retryCount = 0;
    return;
  }
  retryCount++;
  const backoff = Math.min(1000 * Math.pow(2, retryCount), 10000);
  if (debug) console.log(`[VeilProof] Retry ${retryCount}/${MAX_RETRIES} in ${backoff}ms`);
  await delay(backoff);
  try {
    await fetch(`${endpoint}/api/telemetry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify(payload),
      keepalive: true,
    });
    retryCount = 0;
  } catch (err) {
    if (debug) console.error('[VeilProof] Retry failed:', (err as Error).message);
  }
}

/**
 * Send session start notification.
 */
export async function sendSessionStart(): Promise<void> {
  if (!endpoint) return;
  try {
    await fetch(`${endpoint}/api/session/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({
        sessionId: getSessionId(),
        meta: getSessionMeta(),
      }),
      keepalive: true,
    });
    if (debug) console.log('[VeilProof] Session start sent');
  } catch (err) {
    if (debug) console.error('[VeilProof] Session start failed:', (err as Error).message);
  }
}

/**
 * Send session end notification.
 */
export async function sendSessionEnd(): Promise<void> {
  if (!endpoint) return;
  try {
    await fetch(`${endpoint}/api/session/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({
        sessionId: getSessionId(),
        duration: Date.now() - (getSessionMeta().startTime || Date.now()),
      }),
      keepalive: true,
    });
    if (debug) console.log('[VeilProof] Session end sent');
  } catch (err) {
    if (debug) console.error('[VeilProof] Session end failed:', (err as Error).message);
  }
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
