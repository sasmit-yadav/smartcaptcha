/**
 * SmartCaptcha SDK — Main Entry Point
 * 
 * Usage:
 *   SmartCaptcha.init({
 *     apiKey: "demo-key",
 *     endpoint: "http://localhost:8000",
 *     debug: true
 *   })
 */

import { initSession, getSessionId, getSessionMeta } from './core/session.js';
import { initBuffer, push, stopBuffer } from './core/buffer.js';
import { initTransport, sendSessionStart, sendSessionEnd } from './core/transport.js';
import { startMouseTracking, stopMouseTracking } from './collectors/mouse.js';
import { startClickTracking, stopClickTracking } from './collectors/click.js';
import { startKeyboardTracking, stopKeyboardTracking } from './collectors/keyboard.js';
import { startScrollTracking, stopScrollTracking } from './collectors/scroll.js';
import { startFocusTracking, stopFocusTracking } from './collectors/focus.js';
import { startTouchTracking, stopTouchTracking } from './collectors/touch.js';

let initialized = false;
let debug = false;

const SmartCaptcha = {
  /**
   * Initialize SmartCaptcha SDK.
   * @param {Object} config
   * @param {string} config.apiKey - Your API key
   * @param {string} config.endpoint - Backend API URL (e.g. "http://localhost:8000")
   * @param {boolean} [config.debug=false] - Enable console logging
   */
  init(config = {}) {
    if (initialized) {
      if (debug) console.warn('[SmartCaptcha] Already initialized');
      return;
    }

    if (!config.apiKey) {
      console.error('[SmartCaptcha] apiKey is required');
      return;
    }

    debug = config.debug || false;

    // 1. Initialize session
    initSession();

    // 2. Initialize transport
    initTransport({
      endpoint: config.endpoint || 'http://localhost:8000',
      apiKey: config.apiKey,
      debug,
    });

    // 3. Initialize buffer
    initBuffer({ debug });

    // 4. Start all collectors
    startMouseTracking(push);
    startClickTracking(push);
    startKeyboardTracking(push);
    startScrollTracking(push);
    startFocusTracking(push);

    // Touch only on touch devices
    if ('ontouchstart' in window) {
      startTouchTracking(push);
    }

    // 5. Notify backend of session start
    sendSessionStart();

    // 6. Send session end on page unload
    window.addEventListener('beforeunload', () => {
      sendSessionEnd();
    });

    initialized = true;

    if (debug) {
      console.log('[SmartCaptcha] Initialized ✓');
      console.log(`[SmartCaptcha] Session: ${getSessionId().slice(-8)}`);
      console.log(`[SmartCaptcha] Endpoint: ${config.endpoint}`);
      console.log('[SmartCaptcha] Collectors: mouse, click, keyboard, scroll, focus' + ('ontouchstart' in window ? ', touch' : ''));
    }
  },

  /**
   * Stop all tracking and flush remaining events.
   */
  destroy() {
    if (!initialized) return;
    stopMouseTracking();
    stopClickTracking();
    stopKeyboardTracking();
    stopScrollTracking();
    stopFocusTracking();
    stopTouchTracking();
    stopBuffer();
    sendSessionEnd();
    initialized = false;
    if (debug) console.log('[SmartCaptcha] Destroyed');
  },

  /** Get current session ID */
  getSessionId,

  /** Get current session metadata */
  getSessionMeta,
};

// Expose globally
window.SmartCaptcha = SmartCaptcha;

export default SmartCaptcha;
