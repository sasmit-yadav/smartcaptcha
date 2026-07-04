/**
 * Touch Collector — tracks touch events for mobile devices.
 * Captures: position, differentiates tap vs swipe vs long-press.
 */

import type { TelemetryEvent } from '../types.js';

let active = false;
let lastCapture = 0;
let pushEvent: ((event: TelemetryEvent) => void) | null = null;
let touchStartT = 0;
let touchStartX = 0;
let touchStartY = 0;
const THROTTLE_MS = 50;

function onTouchStart(e: TouchEvent): void {
  const touch = e.touches[0];
  touchStartT = Date.now();
  touchStartX = touch.clientX;
  touchStartY = touch.clientY;

  pushEvent!({
    type: 'tc',
    action: 'start',
    x: touch.clientX,
    y: touch.clientY,
    t: Date.now(),
    force: touch.force || null,
  });
}

function onTouchMove(e: TouchEvent): void {
  const now = Date.now();
  if (now - lastCapture < THROTTLE_MS) return;
  lastCapture = now;

  const touch = e.touches[0];
  pushEvent!({
    type: 'tc',
    action: 'move',
    x: touch.clientX,
    y: touch.clientY,
    t: now,
    force: touch.force || null,
  });
}

function onTouchEnd(e: TouchEvent): void {
  const now = Date.now();
  const duration = now - touchStartT;
  const endX = e.changedTouches[0]?.clientX || touchStartX;
  const endY = e.changedTouches[0]?.clientY || touchStartY;
  const dx = Math.abs(endX - touchStartX);
  const dy = Math.abs(endY - touchStartY);
  const dist = Math.sqrt(dx * dx + dy * dy);

  // Classify: tap (< 300ms, < 10px), swipe (dist > 50px), long-press (> 500ms)
  let gesture = 'tap';
  if (duration > 500 && dist < 10) gesture = 'longpress';
  else if (dist > 50) gesture = 'swipe';

  // Swipe velocity (px/sec)
  const swipeVel = duration > 0 ? Math.round((dist / duration) * 1000 * 10) / 10 : 0;

  pushEvent!({
    type: 'tc',
    action: 'end',
    x: endX,
    y: endY,
    t: now,
    duration,
    gesture,
    swipeDist: Math.round(dist * 10) / 10,
    swipeVel,
  });
}

export function startTouchTracking(push: (event: TelemetryEvent) => void): void {
  if (active) return;
  pushEvent = push;
  active = true;
  lastCapture = 0;
  document.addEventListener('touchstart', onTouchStart, { passive: true });
  document.addEventListener('touchmove', onTouchMove, { passive: true });
  document.addEventListener('touchend', onTouchEnd, { passive: true });
}

export function stopTouchTracking(): void {
  if (!active) return;
  active = false;
  document.removeEventListener('touchstart', onTouchStart);
  document.removeEventListener('touchmove', onTouchMove);
  document.removeEventListener('touchend', onTouchEnd);
}
