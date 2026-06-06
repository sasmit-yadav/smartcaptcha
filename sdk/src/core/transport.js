/**
 * Transport Layer — sends telemetry batches to the backend API.
 * Uses fetch with keepalive for unload safety.
 * Retries on 5xx with exponential backoff.
 */

import { getSessionId, getSessionMeta } from './session.js';

let endpoint = '';
let apiKey = '';
let debug = false;
let retryCount = 0;
const MAX_RETRIES = 3;

export function initTransport(config) {
  endpoint = config.endpoint;
  apiKey = config.apiKey;
  debug = config.debug || false;
}

/**
 * Send a batch of events to the backend.
 */
export async function sendBatch(events) {
  if (!endpoint) {
    if (debug) console.warn('[SmartCaptcha] No endpoint configured, dropping batch');
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
      if (debug) console.log(`[SmartCaptcha] Batch sent: ${events.length} events queued`);
      return;
    }

    if (res.status === 429) {
      // Rate limited — back off
      if (debug) console.warn('[SmartCaptcha] Rate limited (429), backing off');
      await delay(2000);
      retrySend(payload);
      return;
    }

    if (res.status >= 500) {
      // Server error — retry
      if (debug) console.warn(`[SmartCaptcha] Server error ${res.status}, retrying`);
      retrySend(payload);
      return;
    }

    if (res.status >= 400) {
      // Client error — don't retry
      if (debug) console.error(`[SmartCaptcha] Client error ${res.status}, not retrying`);
    }
  } catch (err) {
    if (debug) console.error('[SmartCaptcha] Network error:', err.message);
    retrySend(payload);
  }
}

async function retrySend(payload) {
  if (retryCount >= MAX_RETRIES) {
    if (debug) console.warn('[SmartCaptcha] Max retries reached, dropping batch');
    retryCount = 0;
    return;
  }
  retryCount++;
  const backoff = Math.min(1000 * Math.pow(2, retryCount), 10000);
  if (debug) console.log(`[SmartCaptcha] Retry ${retryCount}/${MAX_RETRIES} in ${backoff}ms`);
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
    if (debug) console.error('[SmartCaptcha] Retry failed:', err.message);
  }
}

/**
 * Send session start notification.
 */
export async function sendSessionStart() {
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
    if (debug) console.log('[SmartCaptcha] Session start sent');
  } catch (err) {
    if (debug) console.error('[SmartCaptcha] Session start failed:', err.message);
  }
}

/**
 * Send session end notification.
 */
export async function sendSessionEnd() {
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
    if (debug) console.log('[SmartCaptcha] Session end sent');
  } catch (err) {
    if (debug) console.error('[SmartCaptcha] Session end failed:', err.message);
  }
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
