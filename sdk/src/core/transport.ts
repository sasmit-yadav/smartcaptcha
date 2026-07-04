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

export function initTransport(config: { endpoint: string; apiKey: string; debug?: boolean }): void {
  endpoint = config.endpoint;
  apiKey = config.apiKey;
  debug = config.debug || false;
}

/**
 * Send a batch of events to the backend.
 */
export async function sendBatch(events: TelemetryEvent[]): Promise<void> {
  if (!endpoint) {
    if (debug) console.warn('[NextCaptcha] No endpoint configured, dropping batch');
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
      if (debug) console.log(`[NextCaptcha] Batch sent: ${events.length} events queued`);
      return;
    }

    if (res.status === 429) {
      // Rate limited — back off
      if (debug) console.warn('[NextCaptcha] Rate limited (429), backing off');
      await delay(2000);
      retrySend(payload);
      return;
    }

    if (res.status >= 500) {
      // Server error — retry
      if (debug) console.warn(`[NextCaptcha] Server error ${res.status}, retrying`);
      retrySend(payload);
      return;
    }

    if (res.status >= 400) {
      // Client error — don't retry
      // Suppress 404 errors for lightweight backends that don't have telemetry endpoints
      if (res.status !== 404 && debug) {
        console.error(`[NextCaptcha] Client error ${res.status}, not retrying`);
      }
    }
  } catch (err) {
    if (debug) console.error('[NextCaptcha] Network error:', (err as Error).message);
    retrySend(payload);
  }
}

async function retrySend(payload: unknown): Promise<void> {
  if (retryCount >= MAX_RETRIES) {
    if (debug) console.warn('[NextCaptcha] Max retries reached, dropping batch');
    retryCount = 0;
    return;
  }
  retryCount++;
  const backoff = Math.min(1000 * Math.pow(2, retryCount), 10000);
  if (debug) console.log(`[NextCaptcha] Retry ${retryCount}/${MAX_RETRIES} in ${backoff}ms`);
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
    if (debug) console.error('[NextCaptcha] Retry failed:', (err as Error).message);
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
    if (debug) console.log('[NextCaptcha] Session start sent');
  } catch (err) {
    if (debug) console.error('[NextCaptcha] Session start failed:', (err as Error).message);
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
    if (debug) console.log('[NextCaptcha] Session end sent');
  } catch (err) {
    if (debug) console.error('[NextCaptcha] Session end failed:', (err as Error).message);
  }
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
