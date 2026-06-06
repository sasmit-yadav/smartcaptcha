/**
 * EcoHub — Session Manager
 * Generates and persists a session ID.
 */

const SESSION_KEY = 'sc_session_id';

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
  };
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
