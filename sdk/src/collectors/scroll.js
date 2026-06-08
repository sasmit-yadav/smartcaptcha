/**
 * Scroll Collector — tracks scroll position with throttling.
 * Captures: scrollY, velocity, direction reversals, pauses, max depth.
 */

let active = false;
let lastCapture = 0;
let lastY = 0;
let lastT = 0;
let lastDir = 0; // 1 = down, -1 = up
let reversalCount = 0;
let maxDepth = 0;
let pauseCount = 0;
let pauseTimer = null;
const THROTTLE_MS = 100;
const PAUSE_THRESHOLD_MS = 500;
let pushEvent = null;

function handler() {
  const now = Date.now();
  const y = window.scrollY;

  // Pause detection — fires when scrolling stops for > 500ms
  if (pauseTimer) clearTimeout(pauseTimer);
  pauseTimer = setTimeout(() => {
    pauseCount++;
    pushEvent({
      type: 'sc',
      y: window.scrollY,
      t: Date.now(),
      vel: 0,
      rev: false,
      pause: true,
    });
  }, PAUSE_THRESHOLD_MS);

  const dt = now - lastT;
  const dy = y - lastY;
  const dir = dy > 0 ? 1 : dy < 0 ? -1 : lastDir;
  const reversal = lastDir !== 0 && dir !== lastDir && dir !== 0;

  // Always capture direction reversals (even when throttled)
  if (reversal) {
    reversalCount++;
    lastDir = dir;
    lastY = y;
    lastT = now;
    lastCapture = now;
    pushEvent({
      type: 'sc',
      y,
      t: now,
      vel: 0,
      rev: true,
      pause: false,
    });
    return;
  }

  if (now - lastCapture < THROTTLE_MS) return;

  const vel = dt > 0 ? Math.round(Math.abs(dy) / (dt / 1000)) : 0;
  lastDir = dir;

  const docH = document.documentElement.scrollHeight - window.innerHeight;
  const depth = docH > 0 ? Math.round((y / docH) * 100) : 0;
  if (depth > maxDepth) maxDepth = depth;

  lastY = y;
  lastT = now;
  lastCapture = now;

  pushEvent({
    type: 'sc',
    y,
    t: now,
    vel,
    rev: false,
    pause: false,
  });
}

export function startScrollTracking(push) {
  if (active) return;
  pushEvent = push;
  active = true;
  lastY = window.scrollY;
  lastT = Date.now();
  lastDir = 0;
  reversalCount = 0;
  maxDepth = 0;
  pauseCount = 0;
  document.addEventListener('scroll', handler, { passive: true });
}

export function stopScrollTracking() {
  if (!active) return;
  active = false;
  if (pauseTimer) clearTimeout(pauseTimer);
  document.removeEventListener('scroll', handler);
}

export function getScrollStats() {
  return { reversalCount, maxDepth, pauseCount };
}
