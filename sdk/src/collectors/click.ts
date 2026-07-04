/**
 * Click Collector — tracks clicks with inter-click timing.
 * Captures: position, target tag, interval since last click, double-clicks.
 * V2 additions: hover duration, overshoot ratio.
 * Does NOT capture: href, form values, text content (PII-safe).
 */

import type { TelemetryEvent } from '../types.js';

let active = false;
let lastClickT = 0;
let pushEvent: ((event: TelemetryEvent) => void) | null = null;
const DOUBLE_CLICK_MS = 300;

// Track hover timing for each element
const hoverStartTimes = new Map<Element, number>();

function handleMouseEnter(e: MouseEvent): void {
  hoverStartTimes.set(e.target as Element, Date.now());
}

function handleMouseLeave(e: MouseEvent): void {
  hoverStartTimes.delete(e.target as Element);
}

function handler(e: MouseEvent): void {
  const now = Date.now();
  const interval = lastClickT > 0 ? now - lastClickT : null;
  const isDouble = interval !== null && interval < DOUBLE_CLICK_MS;
  lastClickT = now;

  let tw: number | null = null;
  let th: number | null = null;
  let centerX: number | null = null;
  let centerY: number | null = null;
  try {
    const rect = (e.target as Element).getBoundingClientRect();
    tw = Math.round(rect.width);
    th = Math.round(rect.height);
    centerX = rect.left + rect.width / 2;
    centerY = rect.top + rect.height / 2;
  } catch (_) {}

  // Calculate hover duration
  let hoverDuration: number | null = null;
  const hoverStart = hoverStartTimes.get(e.target as Element);
  if (hoverStart) {
    hoverDuration = now - hoverStart;
  }

  // Calculate overshoot ratio (distance from click to target center)
  let overshootRatio: number | null = null;
  if (centerX !== null && centerY !== null && tw !== null && th !== null) {
    const dx = e.clientX - centerX;
    const dy = e.clientY - centerY;
    const distanceToCenter = Math.sqrt(dx * dx + dy * dy);
    const maxDistance = Math.sqrt((tw/2) ** 2 + (th/2) ** 2);
    if (maxDistance > 0) {
      overshootRatio = distanceToCenter / maxDistance;
    }
  }

  pushEvent!({
    type: 'cl',
    x: e.clientX,
    y: e.clientY,
    t: now,
    target: (e.target as Element).tagName,
    interval,
    double: isDouble,
    tw,
    th,
    hoverDuration,
    overshootRatio,
  });
}

export function startClickTracking(push: (event: TelemetryEvent) => void): void {
  if (active) return;
  pushEvent = push;
  active = true;
  lastClickT = 0;
  document.addEventListener('click', handler, { passive: true });
  document.addEventListener('mouseenter', handleMouseEnter, { passive: true, capture: true });
  document.addEventListener('mouseleave', handleMouseLeave, { passive: true, capture: true });
}

export function stopClickTracking(): void {
  if (!active) return;
  active = false;
  document.removeEventListener('click', handler);
  document.removeEventListener('mouseenter', handleMouseEnter, true);
  document.removeEventListener('mouseleave', handleMouseLeave, true);
  hoverStartTimes.clear();
}
