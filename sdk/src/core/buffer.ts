/**
 * Event Buffer — batches events and flushes on interval or threshold.
 * Flush triggers: every 5s, 100 events, or page unload.
 */

import type { TelemetryEvent } from '../types.js';
import { sendBatch } from './transport.js';

const FLUSH_INTERVAL_MS = 5000;
const MAX_BUFFER_SIZE = 100;

let events: TelemetryEvent[] = [];
let flushTimer: number | null = null;
let debug = false;
let telemetryDisabled = false;

export function initBuffer(options: { debug?: boolean; disableTelemetry?: boolean } = {}): void {
  debug = options.debug || false;
  telemetryDisabled = options.disableTelemetry || false;

  if (telemetryDisabled) {
    if (debug) console.log('[VeriFlow] Telemetry disabled - events will not be sent');
    return;
  }

  // Periodic flush
  flushTimer = window.setInterval(flush, FLUSH_INTERVAL_MS);

  // Flush on page unload
  window.addEventListener('beforeunload', flush);
  window.addEventListener('pagehide', flush);

  if (debug) console.log('[VeriFlow] Buffer initialized (flush every 5s or 100 events)');
}

export function push(event: TelemetryEvent): void {
  events.push(event);
  if (debug && events.length === 1) console.log('[VeriFlow] First event captured');

  // Auto-flush when buffer is full
  if (events.length >= MAX_BUFFER_SIZE) {
    flush();
  }
}

export function flush(): void {
  if (events.length === 0) return;

  const batch = events.splice(0, events.length);

  if (debug) {
    console.log(`[VeriFlow] Flushing ${batch.length} events`);
  }

  sendBatch(batch);
}

export function stopBuffer(): void {
  if (flushTimer) clearInterval(flushTimer);
  flush(); // Final flush
}

export function getBufferSize(): number {
  return events.length;
}

export function getEvents(): TelemetryEvent[] {
  return [...events]; // Return a copy to prevent external modification
}
