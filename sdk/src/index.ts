/**
 * VeriFlow SDK — Main Entry Point
 *
 * Usage:
 *   VeriFlow.init({
 *     apiKey: "your-api-key",
 *     endpoint: "https://api.veriflow.com",
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
import { computeFeatures } from './core/features.js';

import type {
  VeriFlowConfig,
  DecisionResult,
  DebugSnapshot,
  SelfTestResult,
  DecisionCallback,
  SelfTestCallback
} from './types.js';

/**
 * Validate configuration and provide helpful error messages
 */
function validateConfig(config: VeriFlowConfig): { valid: boolean; error?: string } {
  if (!config.apiKey || typeof config.apiKey !== 'string') {
    return { valid: false, error: 'apiKey is required and must be a string' };
  }

  // Validate API key format (production keys start with vf_ or sc_ prefixes)
  const validPrefixes = ['vf_live_', 'vf_test_', 'vf_admin_', 'sc_live_', 'sc_test_', 'sc_admin_'];
  const hasValidPrefix = validPrefixes.some(prefix => config.apiKey.startsWith(prefix));
  
  if (!hasValidPrefix && config.apiKey !== 'demo-key') {
    return { valid: false, error: 'Invalid API key format. Production keys must start with vf_ or sc_ prefixes' };
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

const SDK_VERSION = '0.2.0';
const DEFAULT_ENDPOINT = 'https://next-captcha-sdk.onrender.com';

/** Run a collector lifecycle call without letting an internal bug crash the host page (S2.1). */
function safeCall(name: string, fn: () => void): void {
  try {
    fn();
  } catch (error) {
    console.warn(`[VeriFlow] "${name}" failed and was suppressed:`, error);
  }
}
let initialized = false;
let debug = false;
let initConfig: VeriFlowConfig | null = null;

interface VeriFlowAPI {
  init(config: VeriFlowConfig): void;
  destroy(): void;
  getSessionId(): string;
  getSessionMeta(): import('./types.js').SessionMeta;
  getDecision(callback: DecisionCallback): void;
  getDebugSnapshot(): DebugSnapshot;
  selfTest(callback: SelfTestCallback): void;
}

// No-op version for SSR/Node environments
const VeriFlowSSR: VeriFlowAPI = {
  init: () => console.warn('[VeriFlow] Running in SSR environment - SDK disabled'),
  destroy: () => {},
  getSessionId: () => '',
  getSessionMeta: () => ({ sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false }),
  getDecision: (callback: DecisionCallback) => callback({ error: 'SSR environment', action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 }),
  getDebugSnapshot: () => ({ version: SDK_VERSION, initialized: false, debug: false, session: { id: '', meta: { sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false } }, buffer: { eventCount: 0, recentEvents: [] }, collectors: { mouse: false, click: false, keyboard: false, scroll: false, focus: false, touch: false } }),
  selfTest: (callback: SelfTestCallback) => callback({ version: SDK_VERSION, tests: [{ name: 'SSR Environment', status: 'warn', error: 'SDK disabled in SSR' }], passed: 0, failed: 0, overall: 'unknown' })
};

const VeriFlow: VeriFlowAPI = {
  /**
   * Initialize VeriFlow SDK.
   */
  init(config: VeriFlowConfig = { apiKey: '' }) {
    if (!isBrowser) {
      console.warn('[VeriFlow] Running in SSR environment - SDK disabled');
      return;
    }

    if (initialized) {
      if (debug) console.warn('[VeriFlow] Already initialized');
      return;
    }

    // Validate configuration
    const validation = validateConfig(config);
    if (!validation.valid) {
      const errorMsg = `[VeriFlow] Configuration error: ${validation.error}. Get an API key at https://veriflow.com/dashboard`;
      if (debug) {
        throw new Error(errorMsg);
      } else {
        console.warn(errorMsg);
        return;
      }
    }

    debug = config.debug || false;
    initConfig = config;
    
    // 1. Initialize session with source (default to 'demo' for backward compatibility)
    initSession(config.source || 'demo');

    // 2. Initialize transport - use provided endpoint or default to production
    initTransport({
      endpoint: config.endpoint || DEFAULT_ENDPOINT,
      apiKey: config.apiKey,
      debug,
    });

    // 3. Initialize buffer (disable telemetry if configured)
    initBuffer({ debug, disableTelemetry: config.disableTelemetry });

    // 4. Start all collectors — each wrapped so a collector bug can't crash the host page
    safeCall('startMouseTracking', () => startMouseTracking(push));
    safeCall('startClickTracking', () => startClickTracking(push));
    safeCall('startKeyboardTracking', () => startKeyboardTracking(push));
    safeCall('startScrollTracking', () => startScrollTracking(push));
    safeCall('startFocusTracking', () => startFocusTracking(push));

    // Touch only on touch devices
    if ('ontouchstart' in window) {
      safeCall('startTouchTracking', () => startTouchTracking(push));
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
      console.log(`[VeriFlow] v${SDK_VERSION} Initialized ✓`);
      console.log(`[VeriFlow] Session: ${getSessionId().slice(-8)}`);
      console.log(`[VeriFlow] Endpoint: ${config.endpoint}`);
      console.log('[VeriFlow] Collectors: mouse, click, keyboard, scroll, focus' + ('ontouchstart' in window ? ', touch' : ''));
    }
  },

  /**
   * Stop all tracking and flush remaining events.
   */
  destroy(): void {
    if (!initialized || !isBrowser) return;
    safeCall('stopMouseTracking', stopMouseTracking);
    safeCall('stopClickTracking', stopClickTracking);
    safeCall('stopKeyboardTracking', stopKeyboardTracking);
    safeCall('stopScrollTracking', stopScrollTracking);
    safeCall('stopFocusTracking', stopFocusTracking);
    safeCall('stopTouchTracking', stopTouchTracking);
    safeCall('stopBuffer', stopBuffer);
    safeCall('sendSessionEnd', () => { sendSessionEnd(); });
    initialized = false;
    if (debug) console.log('[VeriFlow] Destroyed');
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
      VeriFlowSSR.getDecision(callback);
      return;
    }

    if (!initialized) {
      callback({ error: 'VeriFlow not initialized. Call init() first.', action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
      return;
    }

    try {
      // Get collected events
      const events = getEvents();
      const sessionMeta = getSessionMeta();
      
      if (debug) {
        console.log('[VeriFlow] Getting decision...');
        console.log(`[VeriFlow] Events collected: ${events.length}`);
      }

      // Extract features from events (V4 feature set)
      const features = computeFeatures(events, sessionMeta);
      
      if (debug) {
        console.log('[VeriFlow] Computed features:', Object.keys(features).slice(0, 10), '...');
        console.log('[VeriFlow] Total feature count:', Object.keys(features).length);
        console.log('[VeriFlow] Sample feature values:', {
          avg_hover_duration: features.avg_hover_duration,
          avg_overshoot_ratio: features.avg_overshoot_ratio,
          mouse_curvature_std: features.mouse_curvature_std,
          mouse_jerk_std: features.mouse_jerk_std
        });
      }
      
      // Add fingerprint data
      const fingerprint = {
        webdriver_flag: sessionMeta.webdriverFlag || false,
        user_agent: sessionMeta.userAgent || '',
        has_touch: sessionMeta.hasTouch || false,
        platform: sessionMeta.platform || 'unknown'
      };

      const requestBody = {
        sdkVersion: SDK_VERSION,
        ...features,
        ...fingerprint
      };
      
      if (debug) {
        console.log('[VeriFlow] Request body keys:', Object.keys(requestBody).slice(0, 25));
        console.log('[VeriFlow] Total request body keys:', Object.keys(requestBody).length);
      }

      // Send to prediction API - use init config or default to production
      const endpoint = initConfig?.endpoint || DEFAULT_ENDPOINT;
      const apiKey = initConfig?.apiKey || '';
      
      if (!apiKey) {
        callback({ error: 'API key not provided', action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
        return;
      }
      
      fetch(`${endpoint}/api/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(requestBody)
      })
      .then(async response => {
        const body = await response.json().catch(() => ({}));

        if (!response.ok) {
          // Non-2xx: body is an error shape (e.g. FastAPI's {detail: "..."}),
          // not a DecisionResult — never pass it through as-is (previously
          // caused a downstream crash when callers read result.action).
          const message = body?.detail || body?.error || `Request failed with status ${response.status}`;
          if (debug) console.warn('[VeriFlow] Prediction request failed:', message);
          callback({ error: message, action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
          return;
        }

        if (debug) {
          console.log('[VeriFlow] Decision received:', body);
        }
        callback(body as DecisionResult);
      })
      .catch(error => {
        console.error('[VeriFlow] Prediction error:', error);
        callback({ error: (error as Error).message, action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
      });

    } catch (error) {
      console.error('[VeriFlow] getDecision error:', error);
      callback({ error: (error as Error).message, action: 'block', bot_probability: 1, risk_score: 100, confidence: 0, risk_engine_enabled: false, behavior_score: 0, fingerprint_score: 0, overall_risk: 100 });
    }
  },

  /**
   * Get debug snapshot for troubleshooting
   * Returns current SDK state including buffer, session meta, and recent events
   */
  getDebugSnapshot(): DebugSnapshot {
    if (!isBrowser) {
      return VeriFlowSSR.getDebugSnapshot();
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
      VeriFlowSSR.selfTest(callback);
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
    const apiKey = (window as any).VERIFLOW_CONFIG?.API_KEY;
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

    // Test 4: Network connectivity check - use config.js if available
    const endpoint = (window as any).VERIFLOW_CONFIG?.BACKEND_URL || initConfig?.endpoint || DEFAULT_ENDPOINT;
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
        if (debug) console.log('[VeriFlow] Self-test results:', results);
        callback(results);
      })
      .catch(error => {
        results.tests.push({ name: 'Network Reachable', status: 'fail', error: (error as Error).message });
        results.failed++;
        results.overall = results.failed === 0 ? 'pass' : 'fail';
        if (debug) console.log('[VeriFlow] Self-test results:', results);
        callback(results);
      });
  },
};

// Export for esbuild to handle global exposure
export default VeriFlow;

// Manual global exposure for browser usage (outside of esbuild's control)
if (typeof window !== 'undefined') {
  (window as any).VeriFlow = VeriFlow;
}
