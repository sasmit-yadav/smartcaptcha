/**
 * Keyboard Collector — tracks keydown/keyup timing.
 * NEVER captures actual key values for printable characters (PII-safe).
 * Only safe keys: Backspace, Tab, Enter, ArrowKeys.
 * All other keys recorded as "CHAR" (anonymized).
 */

import type { TelemetryEvent } from '../types.js';

let active = false;
let pushEvent: ((event: TelemetryEvent) => void) | null = null;
let lastKeyUpT = 0;
let lastKeyDownT = 0;
let backspaceCount = 0;
const SAFE_KEYS = new Set([
  'Backspace', 'Tab', 'Enter',
  'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
]);

function sanitizeKey(key: string): string {
  return SAFE_KEYS.has(key) ? key : 'CHAR';
}

function onKeyDown(e: KeyboardEvent): void {
  const now = Date.now();
  const safeKey = sanitizeKey(e.key);

  // Inter-key interval (since last keyup)
  const iki = lastKeyUpT > 0 ? now - lastKeyUpT : null;

  lastKeyDownT = now;

  pushEvent!({
    type: 'kd',
    k: safeKey,
    t: now,
    iki,
  });
}

function onKeyUp(e: KeyboardEvent): void {
  const now = Date.now();
  const safeKey = sanitizeKey(e.key);

  // Hold duration: keyup.t - keydown.t
  const hold = lastKeyDownT > 0 ? now - lastKeyDownT : null;

  if (safeKey === 'Backspace') backspaceCount++;

  lastKeyUpT = now;

  pushEvent!({
    type: 'ku',
    k: safeKey,
    t: now,
    hold,
  });
}

export function startKeyboardTracking(push: (event: TelemetryEvent) => void): void {
  if (active) return;
  pushEvent = push;
  active = true;
  backspaceCount = 0;
  lastKeyUpT = 0;
  lastKeyDownT = 0;
  document.addEventListener('keydown', onKeyDown, { passive: true });
  document.addEventListener('keyup', onKeyUp, { passive: true });
}

export function stopKeyboardTracking(): void {
  if (!active) return;
  active = false;
  document.removeEventListener('keydown', onKeyDown);
  document.removeEventListener('keyup', onKeyUp);
}

export function getKeyboardStats(): { backspaceCount: number } {
  return { backspaceCount };
}
