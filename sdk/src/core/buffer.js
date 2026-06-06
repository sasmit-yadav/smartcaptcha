/**
 * Event Buffer — batches events and flushes on interval or threshold.
 * Flush triggers: every 5s, 100 events, or page unload.
 */

import { sendBatch } from './transport.js';

const FLUSH_INTERVAL_MS = 5000;
const MAX_BUFFER_SIZE = 100;

let events = [];
let flushTimer = null;
let debug = false;

export function initBuffer(options = {}) {
  debug = options.debug || false;

  // Periodic flush
  flushTimer = setInterval(flush, FLUSH_INTERVAL_MS);

  // Flush on page unload
  window.addEventListener('beforeunload', flush);
  window.addEventListener('pagehide', flush);

  if (debug) console.log('[SmartCaptcha] Buffer initialized (flush every 5s or 100 events)');
}

export function push(event) {
  events.push(event);
  if (debug && events.length === 1) console.log('[SmartCaptcha] First event captured');

  // Auto-flush when buffer is full
  if (events.length >= MAX_BUFFER_SIZE) {
    flush();
  }
}

export function flush() {
  if (events.length === 0) return;

  const batch = events.splice(0, events.length);

  if (debug) {
    console.log(`[SmartCaptcha] Flushing ${batch.length} events`);
  }

  sendBatch(batch);
}

export function stopBuffer() {
  if (flushTimer) clearInterval(flushTimer);
  flush(); // Final flush
}

export function getBufferSize() {
  return events.length;
}
