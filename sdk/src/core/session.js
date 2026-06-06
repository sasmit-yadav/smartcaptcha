/**
 * SDK Session Manager — generates and persists session ID.
 * Stored in sessionStorage (clears on tab close).
 */

const SESSION_KEY = 'sc_session_id';
const START_KEY = 'sc_session_start';

let sessionId = null;
let startTime = null;

export function initSession() {
  sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  startTime = sessionStorage.getItem(START_KEY);
  if (!startTime) {
    startTime = Date.now().toString();
    sessionStorage.setItem(START_KEY, startTime);
  }
  startTime = parseInt(startTime, 10);
}

export function getSessionId() {
  if (!sessionId) initSession();
  return sessionId;
}

export function getSessionMeta() {
  const ua = navigator.userAgent;
  const isMobile = /Mobi|Android|iPhone|iPad/i.test(ua);
  return {
    sessionId: getSessionId(),
    startTime: startTime || Date.now(),
    userAgent: ua,
    platform: navigator.platform || 'unknown',
    language: navigator.language || 'unknown',
    screenWidth: screen.width,
    screenHeight: screen.height,
    colorDepth: screen.colorDepth,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    deviceType: isMobile ? 'mobile' : 'desktop',
    hasTouch: 'ontouchstart' in window,
    pageUrl: window.location.href,
    pageTitle: document.title,
    referrer: document.referrer || null,
  };
}

export function getSessionDuration() {
  return startTime ? Date.now() - startTime : 0;
}
