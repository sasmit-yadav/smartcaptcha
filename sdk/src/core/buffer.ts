/**
 * Event Buffer — batches events for telemetry logging AND keeps a
 * persistent per-session history for decision-time feature computation.
 *
 * These are deliberately two separate arrays. `events` is a send-queue:
 * `flush()` drains it every 5s / 100 events / page unload and ships it to
 * /api/telemetry (fire-and-forget logging). `history` is never drained by
 * flush — it accumulates every event for the life of the session, because
 * getDecision()/getToken() need the FULL interaction history to score
 * accurately, not just whatever arrived in the last few seconds. Reusing
 * one array for both jobs meant a real user who took more than ~5s to fill
 * a form had most of their genuine activity wiped out from under the score
 * right before it was computed — it saw only the last sliver of activity
 * and misread a real user as a near-zero-activity bot pattern.
 */

import type { TelemetryEvent } from '../types.js';
import { sendBatch } from './transport.js';

const FLUSH_INTERVAL_MS = 5000;
const MAX_BUFFER_SIZE = 100;
// Memory-safety cap only, not a feature-relevance window — a session this
// long has bigger problems than losing its oldest events.
const MAX_HISTORY_SIZE = 5000;

let events: TelemetryEvent[] = [];
let history: TelemetryEvent[] = [];
let flushTimer: number | null = null;
let debug = false;
let telemetryDisabled = false;

export function initBuffer(options: { debug?: boolean; disableTelemetry?: boolean } = {}): void {
  debug = options.debug || false;
  telemetryDisabled = options.disableTelemetry || false;
  events = [];
  history = [];

  if (telemetryDisabled) {
    if (debug) console.log('[VeilProof] Telemetry disabled - events will not be sent');
    return;
  }

  // Periodic flush
  flushTimer = window.setInterval(flush, FLUSH_INTERVAL_MS);

  // Flush on page unload
  window.addEventListener('beforeunload', flush);
  window.addEventListener('pagehide', flush);

  if (debug) console.log('[VeilProof] Buffer initialized (flush every 5s or 100 events)');
}

export function push(event: TelemetryEvent): void {
  events.push(event);
  history.push(event);
  if (history.length > MAX_HISTORY_SIZE) {
    history.splice(0, history.length - MAX_HISTORY_SIZE);
  }
  if (debug && history.length === 1) console.log('[VeilProof] First event captured');

  // Auto-flush the send-queue when it's full — does not touch history.
  if (events.length >= MAX_BUFFER_SIZE) {
    flush();
  }
}

export function flush(): void {
  if (events.length === 0) return;

  const batch = events.splice(0, events.length);

  if (debug) {
    console.log(`[VeilProof] Flushing ${batch.length} events`);
  }

  sendBatch(batch);
}

export function stopBuffer(): void {
  if (flushTimer) clearInterval(flushTimer);
  flush(); // Final flush of the send-queue
  history = [];
}

export function getBufferSize(): number {
  return events.length;
}

export function getEvents(): TelemetryEvent[] {
  return [...history]; // Return a copy of the full session history to prevent external modification
}
