/**
 * Click Collector — tracks clicks with inter-click timing.
 * Captures: position, target tag, interval since last click, double-clicks.
 * Does NOT capture: href, form values, text content (PII-safe).
 */

let active = false;
let lastClickT = 0;
let pushEvent = null;
const DOUBLE_CLICK_MS = 300;

function handler(e) {
  const now = Date.now();
  const interval = lastClickT > 0 ? now - lastClickT : null;
  const isDouble = interval !== null && interval < DOUBLE_CLICK_MS;
  lastClickT = now;

  let tw = null;
  let th = null;
  try {
    const rect = e.target.getBoundingClientRect();
    tw = Math.round(rect.width);
    th = Math.round(rect.height);
  } catch (_) {}

  pushEvent({
    type: 'cl',
    x: e.clientX,
    y: e.clientY,
    t: now,
    target: e.target.tagName,
    interval,
    double: isDouble,
    tw,
    th,
  });
}

export function startClickTracking(push) {
  if (active) return;
  pushEvent = push;
  active = true;
  lastClickT = 0;
  document.addEventListener('click', handler, { passive: true });
}

export function stopClickTracking() {
  if (!active) return;
  active = false;
  document.removeEventListener('click', handler);
}
