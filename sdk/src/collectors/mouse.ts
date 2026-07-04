/**
 * Mouse Collector — tracks mouse movement with throttling.
 * Captures: position, velocity, angle changes, total distance.
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

  // Angle change (curvature signal)
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

export function startMouseTracking(push: (event: TelemetryEvent) => void): void {
  if (active) return;
  pushEvent = push;
  active = true;
  totalDistance = 0;
  lastAngle = null;
  isFirst = true;
  document.addEventListener('mousemove', handler, { passive: true });
}

export function stopMouseTracking(): void {
  if (!active) return;
  active = false;
  document.removeEventListener('mousemove', handler);
}

export function getMouseStats(): { totalDistance: number } {
  return { totalDistance: Math.round(totalDistance * 10) / 10 };
}
