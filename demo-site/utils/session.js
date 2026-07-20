/**
 * EcoHub — Session Manager
 * Generates and persists a session ID.
 */

const SESSION_KEY = 'sc_session_id';
const SOURCE_KEY = 'sc_source';

/**
 * Get or create a session ID (UUID v4).
 * Stored in sessionStorage so it clears on tab close.
 * @returns {string} UUID
 */
export function getSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/**
 * Return session metadata.
 */
export function getSessionMeta() {
  const ua = navigator.userAgent;
  const isMobile = /Mobi|Android|iPhone|iPad/i.test(ua);

  return {
    sessionId: getSessionId(),
    startTime: getStartTime(),
    userAgent: ua,
    platform: navigator.platform || 'unknown',
    screenWidth: screen.width,
    screenHeight: screen.height,
    deviceType: isMobile ? 'mobile' : 'desktop',
    // Read live on every call (not cached at module load), matching the
    // real SDK's session.ts — navigator.webdriver reflects the CURRENT
    // automation state, which stealth-patched drivers try to hide after
    // page load. This was previously missing entirely from demo-site's
    // inline collector, so every bot session (regardless of driving tool)
    // silently reported a clean fingerprint. Fixed 2026-07-18.
    webdriverFlag: navigator.webdriver === true,
    // Honeypot (strategy step 7): true if the hidden trap field was filled —
    // a near-certain bot, auto-labeled server-side for free training data.
    honeypotTriggered: isHoneypotFilled(),
    // Human-data growth: sessions reached via a link carrying ?src=volunteer
    // get auto-labeled 'human' server-side (see sdk-backend/api/routes/
    // session.py) — a free training label with no manual review needed.
    // Deliberately keyed on HOW the visitor arrived (a marker only ever
    // added to links handed to real people), not on "did they complete the
    // form" — the latter is something bot scripts do too, and would risk
    // mislabeling a bot session 'human' if the bot script's own explicit
    // label_session('bot') call ever fails to run (observed happening in
    // practice — see docs/current_task.md).
    source: getSource(),
  };
}

/**
 * Capture a `?src=volunteer` URL param (only recognized value today) into
 * sessionStorage on first load, so it survives navigation to other demo-site
 * pages within the same tab/session — matches the sc_session_id pattern.
 */
function getSource() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get('src');
  if (fromUrl) {
    sessionStorage.setItem(SOURCE_KEY, fromUrl);
    return fromUrl;
  }
  return sessionStorage.getItem(SOURCE_KEY) || undefined;
}

/**
 * True if any honeypot field on the page has been filled. Honeypot inputs are
 * off-screen and aria-hidden (see the forms), so a real human never touches
 * them; a naive bot that fills every input trips this.
 */
function isHoneypotFilled() {
  const fields = document.querySelectorAll('[data-vp-honeypot]');
  for (const el of fields) {
    if ((el.value || '').trim().length > 0) return true;
  }
  return false;
}

/**
 * Track session start time (epoch ms).
 */
function getStartTime() {
  const KEY = 'sc_session_start';
  let start = sessionStorage.getItem(KEY);
  if (!start) {
    start = Date.now().toString();
    sessionStorage.setItem(KEY, start);
  }
  return parseInt(start, 10);
}

/**
 * Return last 8 chars of session ID for display.
 */
export function getSessionShort() {
  return getSessionId().slice(-8);
}
