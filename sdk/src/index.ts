/**
 * NextCaptcha SDK — Main Entry Point
 *
 * Usage:
 *   NextCaptcha.init({
 *     apiKey: "demo-key",
 *     endpoint: "http://localhost:8000",
 *     debug: true
 *   })
 *
 * Version: 0.1.0
 */

import { initSession, getSessionId, getSessionMeta } from './core/session.js';
import { initBuffer, push, stopBuffer, getEvents } from './core/buffer.js';
import { initTransport, sendSessionStart, sendSessionEnd } from './core/transport.js';
import { startMouseTracking, stopMouseTracking } from './collectors/mouse.js';
import { startClickTracking, stopClickTracking } from './collectors/click.js';
import { startKeyboardTracking, stopKeyboardTracking } from './collectors/keyboard.js';
import { startScrollTracking, stopScrollTracking } from './collectors/scroll.js';
import { startFocusTracking, stopFocusTracking } from './collectors/focus.js';
import { startTouchTracking, stopTouchTracking } from './collectors/touch.js';

import type {
  NextCaptchaConfig,
  DecisionResult,
  DebugSnapshot,
  SelfTestResult,
  DecisionCallback,
  SelfTestCallback,
  TelemetryEvent,
  FeatureVector
} from './types.js';

/**
 * Validate configuration and provide helpful error messages
 */
function validateConfig(config: NextCaptchaConfig): { valid: boolean; error?: string } {
  if (!config.apiKey || typeof config.apiKey !== 'string') {
    return { valid: false, error: 'apiKey is required and must be a string' };
  }

  // Validate API key format (production keys start with sc_live_, sc_test_, or sc_admin_)
  const validPrefixes = ['sc_live_', 'sc_test_', 'sc_admin_'];
  const hasValidPrefix = validPrefixes.some(prefix => config.apiKey.startsWith(prefix));
  
  if (!hasValidPrefix && config.apiKey !== 'demo-key') {
    return { valid: false, error: 'Invalid API key format. Production keys must start with sc_live_, sc_test_, or sc_admin_' };
  }

  if (config.endpoint && typeof config.endpoint !== 'string') {
    return { valid: false, error: 'endpoint must be a string if provided' };
  }

  if (config.debug !== undefined && typeof config.debug !== 'boolean') {
    return { valid: false, error: 'debug must be a boolean if provided' };
  }

  return { valid: true };
}

// Check for browser environment (SSR safety)
const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

const SDK_VERSION = '0.1.0';
let initialized = false;
let debug = false;

interface NextCaptchaAPI {
  init(config: NextCaptchaConfig): void;
  destroy(): void;
  getSessionId(): string;
  getSessionMeta(): import('./types.js').SessionMeta;
  getDecision(callback: DecisionCallback): void;
  getDebugSnapshot(): DebugSnapshot;
  selfTest(callback: SelfTestCallback): void;
}

// No-op version for SSR/Node environments
const NextCaptchaSSR: NextCaptchaAPI = {
  init: () => console.warn('[NextCaptcha] Running in SSR environment - SDK disabled'),
  destroy: () => {},
  getSessionId: () => '',
  getSessionMeta: () => ({ sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false }),
  getDecision: (callback: DecisionCallback) => callback({ error: 'SSR environment', action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 }),
  getDebugSnapshot: () => ({ version: '0.1.0', initialized: false, debug: false, session: { id: '', meta: { sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false } }, buffer: { eventCount: 0, recentEvents: [] }, collectors: { mouse: false, click: false, keyboard: false, scroll: false, focus: false, touch: false } }),
  selfTest: (callback: SelfTestCallback) => callback({ version: '0.1.0', tests: [{ name: 'SSR Environment', status: 'warn', error: 'SDK disabled in SSR' }], passed: 0, failed: 0, overall: 'unknown' })
};

const NextCaptcha: NextCaptchaAPI = {
  /**
   * Initialize NextCaptcha SDK.
   */
  init(config: NextCaptchaConfig = { apiKey: '' }) {
    if (!isBrowser) {
      console.warn('[NextCaptcha] Running in SSR environment - SDK disabled');
      return;
    }

    if (initialized) {
      if (debug) console.warn('[NextCaptcha] Already initialized');
      return;
    }

    // Validate configuration
    const validation = validateConfig(config);
    if (!validation.valid) {
      const errorMsg = `[NextCaptcha] Configuration error: ${validation.error}. Get an API key at https://nextcaptcha.ai/dashboard`;
      if (debug) {
        throw new Error(errorMsg);
      } else {
        console.warn(errorMsg);
        return;
      }
    }

    debug = config.debug || false;

    // 1. Initialize session with source (default to 'demo' for backward compatibility)
    initSession(config.source || 'demo');

    // 2. Initialize transport
    initTransport({
      endpoint: config.endpoint || 'http://localhost:8000',
      apiKey: config.apiKey,
      debug,
    });

    // 3. Initialize buffer (disable telemetry if configured)
    initBuffer({ debug, disableTelemetry: config.disableTelemetry });

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

    // 5. Notify backend of session start (only if telemetry enabled)
    if (!config.disableTelemetry) {
      sendSessionStart();

      // 6. Send session end on page unload (only if telemetry enabled)
      window.addEventListener('beforeunload', () => {
        sendSessionEnd();
      });
    }

    initialized = true;

    if (debug) {
      console.log(`[NextCaptcha] v${SDK_VERSION} Initialized ✓`);
      console.log(`[NextCaptcha] Session: ${getSessionId().slice(-8)}`);
      console.log(`[NextCaptcha] Endpoint: ${config.endpoint}`);
      console.log('[NextCaptcha] Collectors: mouse, click, keyboard, scroll, focus' + ('ontouchstart' in window ? ', touch' : ''));
    }
  },

  /**
   * Stop all tracking and flush remaining events.
   */
  destroy(): void {
    if (!initialized || !isBrowser) return;
    stopMouseTracking();
    stopClickTracking();
    stopKeyboardTracking();
    stopScrollTracking();
    stopFocusTracking();
    stopTouchTracking();
    stopBuffer();
    sendSessionEnd();
    initialized = false;
    if (debug) console.log('[NextCaptcha] Destroyed');
  },

  /** Get current session ID */
  getSessionId,
  /** Get current session metadata */
  getSessionMeta,

  /**
   * Get bot detection decision for current session
   */
  getDecision(callback: DecisionCallback): void {
    if (!isBrowser) {
      NextCaptchaSSR.getDecision(callback);
      return;
    }

    if (!initialized) {
      callback({ error: 'NextCaptcha not initialized. Call init() first.', action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
      return;
    }

    try {
      // Get collected events
      const events = getEvents();
      const sessionMeta = getSessionMeta();
      
      if (debug) {
        console.log('[NextCaptcha] Getting decision...');
        console.log(`[NextCaptcha] Events collected: ${events.length}`);
      }

      // Extract features from events (simplified version)
      const features = extractFeatures(events);
      
      // Add fingerprint data
      const fingerprint = {
        webdriver_flag: sessionMeta.webdriverFlag || false,
        user_agent: sessionMeta.userAgent || '',
        has_touch: sessionMeta.hasTouch || false,
        platform: sessionMeta.platform || 'unknown'
      };

      // Send to prediction API
      const endpoint = (window as any).NEXTCAPTCHA_CONFIG?.BACKEND_URL || 'http://localhost:8000';
      const apiKey = (window as any).NEXTCAPTCHA_CONFIG?.API_KEY || '';
      
      fetch(`${endpoint}/api/predict`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({
          sdkVersion: SDK_VERSION,
          ...features,
          ...fingerprint
        })
      })
      .then(response => response.json())
      .then((data: DecisionResult) => {
        if (debug) {
          console.log('[NextCaptcha] Decision received:', data);
        }
        callback(data);
      })
      .catch(error => {
        console.error('[NextCaptcha] Prediction error:', error);
        callback({ error: (error as Error).message, action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
      });

    } catch (error) {
      console.error('[NextCaptcha] getDecision error:', error);
      callback({ error: (error as Error).message, action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
    }
  },

  /**
   * Get debug snapshot for troubleshooting
   * Returns current SDK state including buffer, session meta, and recent events
   */
  getDebugSnapshot(): DebugSnapshot {
    if (!isBrowser) {
      return NextCaptchaSSR.getDebugSnapshot();
    }

    return {
      version: SDK_VERSION,
      initialized,
      debug,
      session: {
        id: getSessionId(),
        meta: getSessionMeta()
      },
      buffer: {
        eventCount: getEvents().length,
        recentEvents: getEvents().slice(-10) // Last 10 events
      },
      collectors: {
        mouse: true,
        click: true,
        keyboard: true,
        scroll: true,
        focus: true,
        touch: 'ontouchstart' in window
      }
    };
  },

  /**
   * Self-test method to verify SDK integration
   * Checks API key, network connectivity, event collection
   */
  selfTest(callback: SelfTestCallback): void {
    if (!isBrowser) {
      NextCaptchaSSR.selfTest(callback);
      return;
    }

    const results: SelfTestResult = {
      version: SDK_VERSION,
      tests: [],
      passed: 0,
      failed: 0,
      overall: 'unknown'
    };

    // Test 1: Initialization check
    if (initialized) {
      results.tests.push({ name: 'SDK Initialized', status: 'pass' });
      results.passed++;
    } else {
      results.tests.push({ name: 'SDK Initialized', status: 'fail', error: 'SDK not initialized. Call init() first.' });
      results.failed++;
    }

    // Test 2: API key check
    const apiKey = (window as any).NEXTCAPTCHA_CONFIG?.API_KEY;
    if (apiKey) {
      results.tests.push({ name: 'API Key Valid', status: 'pass' });
      results.passed++;
    } else {
      results.tests.push({ name: 'API Key Valid', status: 'fail', error: 'Invalid or missing API key' });
      results.failed++;
    }

    // Test 3: Event collection check
    const eventCount = getEvents().length;
    if (eventCount > 0) {
      results.tests.push({ name: 'Events Collected', status: 'pass', count: eventCount });
      results.passed++;
    } else {
      results.tests.push({ name: 'Events Collected', status: 'warn', error: 'No events collected yet. Interact with the page first.' });
    }

    // Test 4: Network connectivity check
    const endpoint = (window as any).NEXTCAPTCHA_CONFIG?.BACKEND_URL || 'http://localhost:8000';
    fetch(`${endpoint}/health`, { method: 'GET' })
      .then(response => {
        if (response.ok) {
          results.tests.push({ name: 'Network Reachable', status: 'pass' });
          results.passed++;
        } else {
          results.tests.push({ name: 'Network Reachable', status: 'fail', error: `HTTP ${response.status}` });
          results.failed++;
        }
        results.overall = results.failed === 0 ? 'pass' : 'fail';
        if (debug) console.log('[NextCaptcha] Self-test results:', results);
        callback(results);
      })
      .catch(error => {
        results.tests.push({ name: 'Network Reachable', status: 'fail', error: (error as Error).message });
        results.failed++;
        results.overall = results.failed === 0 ? 'pass' : 'fail';
        if (debug) console.log('[NextCaptcha] Self-test results:', results);
        callback(results);
      });
  },
};

/**
 * Extract features from collected events (simplified for customer SDK)
 */
function extractFeatures(events: TelemetryEvent[]): FeatureVector {
  const mouseEvents = events.filter(e => e.type === 'mm');
  const clickEvents = events.filter(e => e.type === 'cl');
  const keyDownEvents = events.filter(e => e.type === 'kd');
  const scrollEvents = events.filter(e => e.type === 'sc');

  // Basic feature extraction
  const mouseVels: number[] = [];
  for (let i = 1; i < mouseEvents.length; i++) {
    const dx = mouseEvents[i].x! - mouseEvents[i-1].x!;
    const dy = mouseEvents[i].y! - mouseEvents[i-1].y!;
    const dt = (mouseEvents[i].t - mouseEvents[i-1].t) / 1000;
    if (dt > 0) {
      const dist = Math.sqrt(dx*dx + dy*dy);
      const vel = dist / dt;
      if (vel > 0 && vel < 10000) mouseVels.push(vel);
    }
  }

  const avgMouseVel = mouseVels.length > 0 ? mouseVels.reduce((a, b) => a + b, 0) / mouseVels.length : 0;
  
  let totalDistance = 0;
  for (let i = 1; i < mouseEvents.length; i++) {
    const dx = mouseEvents[i].x! - mouseEvents[i-1].x!;
    const dy = mouseEvents[i].y! - mouseEvents[i-1].y!;
    totalDistance += Math.sqrt(dx*dx + dy*dy);
  }

  const firstEvent = events[0];
  const lastEvent = events[events.length - 1];
  const sessionDuration = firstEvent && lastEvent ? (lastEvent.t - firstEvent.t) / 1000 : 0;

  // Return V4 feature set with defaults for missing features
  return {
    // V1 Base Features
    mouse_count: mouseEvents.length,
    mouse_vel_mean: avgMouseVel,
    mouse_vel_std: 0,
    mouse_vel_max: 0,
    mouse_accel_mean: 0,
    mouse_accel_std: 0,
    mouse_accel_max: 0,
    mouse_angle_std: 0,
    mouse_angle_p90: 0,
    mouse_path_efficiency: 0,
    mouse_idle_gap_count: 0,
    mouse_event_ratio: mouseEvents.length / events.length,
    click_count: clickEvents.length,
    click_interval_std: 0,
    click_interval_min: 0,
    click_interval_p90: 0,
    double_click_count: 0,
    key_count: keyDownEvents.length,
    iki_p10: 0,
    iki_p50: 0,
    iki_p90: 0,
    hold_std: 0,
    hold_p90: 0,
    backspace_count: 0,
    scroll_count: scrollEvents.length,
    avg_scroll_vel: 0,
    scroll_vel_std: 0,
    scroll_rev_count: 0,
    scroll_pause_count: 0,
    focus_event_count: 0,
    touch_event_count: 0,
    session_duration: sessionDuration,
    event_count: events.length,
    event_rate: events.length / sessionDuration,
    pause_count: 0,
    pause_ratio: 0,
    // V2 Additions
    mouse_vel_p10: 0,
    mouse_vel_p50: 0,
    mouse_vel_p90: 0,
    // V3 Additions
    mouse_curvature_std: 0,
    mouse_jerk_std: 0,
    movement_entropy: 0,
    // V4 Additions
    avg_hover_duration: 0,
    hover_duration_std: 0,
    avg_overshoot_ratio: 0,
    overshoot_ratio_std: 0,
  };
}

// Export for esbuild to handle global exposure
export default NextCaptcha;

// Manual global exposure for browser usage (outside of esbuild's control)
if (typeof window !== 'undefined') {
  (window as any).NextCaptcha = NextCaptcha;
}
