/**
 * SDK Session Manager — generates and persists session ID.
 * Stored in sessionStorage (clears on tab close).
 */

import type { SessionMeta } from '../types.js';
import { detectAutomation } from './automation.js';

const SESSION_KEY = 'sc_session_id';
const START_KEY = 'sc_session_start';
const SOURCE_KEY = 'sc_session_source';

let sessionId: string | null = null;
let startTime: number | null = null;
let automationCache: ReturnType<typeof detectAutomation> | null = null;

export function initSession(source: 'demo' | 'client' | 'script-tag' = 'demo'): void {
  sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  const startTimeStr = sessionStorage.getItem(START_KEY);
  if (!startTimeStr) {
    startTime = Date.now();
    sessionStorage.setItem(START_KEY, startTime.toString());
  } else {
    startTime = parseInt(startTimeStr, 10);
  }
  sessionStorage.setItem(SOURCE_KEY, source);
}

export function getSessionId(): string {
  if (!sessionId) initSession();
  return sessionId!;
}

export function getSessionMeta(): SessionMeta {
  const ua = navigator.userAgent;

  // Stealth kits redefine navigator.webdriver to undefined. detectAutomation()
  // catches that spoof plus Playwright/Selenium globals and CDP leaks.
  if (!automationCache) automationCache = detectAutomation();
  const webdriverFlag =
    Boolean(navigator.webdriver) || automationCache.webdriverFlag;

  // Get source from sessionStorage or use default
  const sourceStr = sessionStorage.getItem(SOURCE_KEY);
  const source = (sourceStr === 'client' || sourceStr === 'demo' || sourceStr === 'script-tag') ? sourceStr : 'demo';

  return {
    sessionId: getSessionId(),
    startTime: startTime || Date.now(),
    userAgent: ua,
    platform: navigator.platform || 'unknown',
    webdriverFlag,
    hasTouch: 'ontouchstart' in window,
    source,
    automationScore: automationCache.automationScore,
    automationSignals: automationCache.signals,
  };
}

export function getSessionDuration(): number {
  return startTime ? Date.now() - startTime : 0;
}
