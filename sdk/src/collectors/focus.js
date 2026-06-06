/**
 * Focus Collector — tracks tab/window focus changes and visibility.
 * Captures: blur/focus transitions, total focused/unfocused time, switch count.
 */

let active = false;
let pushEvent = null;
let switchCount = 0;
let totalFocused = 0;
let totalUnfocused = 0;
let lastStateChange = Date.now();
let isFocused = true;

function onVisibilityChange() {
  const now = Date.now();
  const elapsed = now - lastStateChange;

  if (document.hidden) {
    totalFocused += elapsed;
    isFocused = false;
    switchCount++;
    pushEvent({ type: 'fv', state: 'blur', t: now });
  } else {
    totalUnfocused += elapsed;
    isFocused = true;
    switchCount++;
    pushEvent({ type: 'fv', state: 'focus', t: now });
  }
  lastStateChange = now;
}

function onBlur() {
  if (!isFocused) return;
  const now = Date.now();
  totalFocused += now - lastStateChange;
  isFocused = false;
  switchCount++;
  lastStateChange = now;
  pushEvent({ type: 'fv', state: 'blur', t: now });
}

function onFocus() {
  if (isFocused) return;
  const now = Date.now();
  totalUnfocused += now - lastStateChange;
  isFocused = true;
  switchCount++;
  lastStateChange = now;
  pushEvent({ type: 'fv', state: 'focus', t: now });
}

export function startFocusTracking(push) {
  if (active) return;
  pushEvent = push;
  active = true;
  switchCount = 0;
  totalFocused = 0;
  totalUnfocused = 0;
  isFocused = true;
  lastStateChange = Date.now();
  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('blur', onBlur);
  window.addEventListener('focus', onFocus);
}

export function stopFocusTracking() {
  if (!active) return;
  active = false;
  // Final tally
  const now = Date.now();
  if (isFocused) totalFocused += now - lastStateChange;
  else totalUnfocused += now - lastStateChange;

  document.removeEventListener('visibilitychange', onVisibilityChange);
  window.removeEventListener('blur', onBlur);
  window.removeEventListener('focus', onFocus);
}

export function getFocusStats() {
  return { switchCount, totalFocused, totalUnfocused };
}
