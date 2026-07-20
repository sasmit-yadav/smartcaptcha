/**
 * Mouse Collector — tracks mouse movement with throttling.
 *
 * Also keeps a parallel raw high-rate ring buffer via pointermove +
 * getCoalescedEvents(), for signal processing that needs samples denser
 * than the throttled `mm` stream can provide. Only aggregated results are
 * ever sent over the network — raw samples never leave this ring buffer.
 */

import type { TelemetryEvent } from '../types.js';

let active = false;
let lastCapture = 0;
let lastX = 0;
let lastY = 0;
let totalDistance = 0;
let lastAngle: number | null = null;
let isFirst = true;
const THROTTLE_MS = 50;
let pushEvent: ((event: TelemetryEvent) => void) | null = null;

// --- raw high-rate sampling buffer ---
export interface RawSample { x: number; y: number; t: number; } // t = event.timeStamp (sub-ms, monotonic)
const RAW_CAP = 4000; // ~30-40s at 120Hz; ring buffer
let rawSamples: RawSample[] = [];

function pushRaw(x: number, y: number, t: number): void {
  rawSamples.push({ x, y, t });
  if (rawSamples.length > RAW_CAP) rawSamples.shift();
}

function handler(e: MouseEvent): void {
  const now = Date.now();
  if (now - lastCapture < THROTTLE_MS) return;

  const x = e.clientX;
  const y = e.clientY;

  // Skip first event — no reference point yet
  if (isFirst) {
    lastX = x;
    lastY = y;
    lastCapture = now;
    isFirst = false;
    return;
  }

  // Distance from last point
  const dx = x - lastX;
  const dy = y - lastY;
  const dist = Math.sqrt(dx * dx + dy * dy);
  totalDistance += dist;

  // Velocity (px/sec)
  const dt = now - lastCapture;
  const vel = dt > 0 ? Math.round((dist / dt) * 1000 * 10) / 10 : 0;

  // Angle change
  let angleDelta: number | null = null;
  if (dist > 1) {
    const angle = Math.atan2(dy, dx) * (180 / Math.PI);
    if (lastAngle !== null) {
      angleDelta = Math.abs(angle - lastAngle);
      if (angleDelta > 180) angleDelta = 360 - angleDelta;
    }
    lastAngle = angle;
  }

  lastX = x;
  lastY = y;
  lastCapture = now;

  pushEvent!({
    type: 'mm',
    x,
    y,
    t: now,
    dist: Math.round(dist * 10) / 10,
    ang: angleDelta !== null ? Math.round(angleDelta * 10) / 10 : null,
    vel,
    totalDist: Math.round(totalDistance * 10) / 10,
  });
}

function pointerHandler(e: PointerEvent): void {
  // 1) high-rate raw capture (NOT throttled, NOT sent raw over the network —
  //    only mouse, not touch/pen).
  if (e.pointerType === 'mouse') {
    const coalesced = (typeof e.getCoalescedEvents === 'function')
      ? e.getCoalescedEvents()
      : [e];
    for (const c of coalesced) {
      // c.timeStamp is a high-resolution monotonic ms clock (fractional ms)
      pushRaw(c.clientX, c.clientY, c.timeStamp);
    }
  }

  // 2) existing throttled 'mm' event path — unchanged logic, keep the same
  //    throttle, unconditional on pointer type (preserves existing touch/pen
  //    behavior).
  handler(e as unknown as MouseEvent);
}

export function startMouseTracking(push: (event: TelemetryEvent) => void): void {
  if (active) return;
  pushEvent = push;
  active = true;
  totalDistance = 0;
  lastAngle = null;
  isFirst = true;
  rawSamples = [];
  document.addEventListener('pointermove', pointerHandler, { passive: true });
}

export function stopMouseTracking(): void {
  if (!active) return;
  active = false;
  document.removeEventListener('pointermove', pointerHandler);
}

export function getMouseStats(): { totalDistance: number } {
  return { totalDistance: Math.round(totalDistance * 10) / 10 };
}

// expose the raw buffer to the feature computer
export function getRawSamples(): RawSample[] { return rawSamples.slice(); }
