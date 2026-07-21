/**
 * VeilProof SDK — Main Entry Point
 *
 * Usage:
 *   VeilProof.init({
 *     apiKey: "your-api-key",
 *     endpoint: "https://api.veilproof.com",
 *     debug: true
 *   })
 *
 * Version: 1.0.0
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
import { isHoneypotTriggered } from './core/honeypot.js';
import { runAutoInit } from './autoinit.js';

import type {
  VeilProofConfig,
  DecisionResult,
  DebugSnapshot,
  SelfTestResult,
  DecisionCallback,
  SelfTestCallback,
  TokenResult,
  TokenCallback
} from './types.js';

/**
 * Validate configuration and provide helpful error messages
 */
function validateConfig(config: VeilProofConfig): { valid: boolean; error?: string } {
  if (!config.apiKey || typeof config.apiKey !== 'string') {
    return { valid: false, error: 'apiKey is required and must be a string' };
  }

  // Secret keys (vp_secret_...) are for server-side /api/siteverify calls
  // only. A secret key in browser JS/HTML would be visible to every visitor
  // — hard-reject rather than silently accepting a dangerous misconfiguration.
  if (config.apiKey.startsWith('vp_secret_')) {
    return {
      valid: false,
      error: 'Secret keys must never be used in the browser. Use your site key (vp_site_...) here, and your secret key only on your server for /api/siteverify.'
    };
  }

  // Validate API key format (production keys start with vp_ or sc_ prefixes).
  // TEMP TEST-ONLY: vf_ legacy prefixes added back so this local build can
  // be tested against customer-website-test's still-legacy vf_site_ key
  // (the backend already accepts legacy vf_ keys by DB hash lookup, per
  // docs/current_task.md — this line is not meant to be committed as-is).
  const validPrefixes = ['vp_site_', 'vp_live_', 'vp_test_', 'vp_admin_', 'sc_live_', 'sc_test_', 'sc_admin_', 'vf_site_', 'vf_live_', 'vf_test_'];
  const hasValidPrefix = validPrefixes.some(prefix => config.apiKey.startsWith(prefix));

  if (!hasValidPrefix && config.apiKey !== 'demo-key') {
    return { valid: false, error: 'Invalid API key format. Production keys must start with vp_site_ (or legacy vp_live_/vp_test_) prefixes' };
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

const SDK_VERSION = '1.1.2';
const DEFAULT_ENDPOINT = 'https://api.veilproof.tech';

/** Run a collector lifecycle call without letting an internal bug crash the host page (S2.1). */
function safeCall(name: string, fn: () => void): void {
  try {
    fn();
  } catch (error) {
    console.warn(`[VeilProof] "${name}" failed and was suppressed:`, error);
  }
}
let initialized = false;
let debug = false;
let initConfig: VeilProofConfig | null = null;

interface VeilProofAPI {
  init(config: VeilProofConfig): void;
  destroy(): void;
  getSessionId(): string;
  getSessionMeta(): import('./types.js').SessionMeta;
  getDecision(callback: DecisionCallback): void;
  getToken(callback: TokenCallback): void;
  getToken(): Promise<TokenResult>;
  getDebugSnapshot(): DebugSnapshot;
  selfTest(callback: SelfTestCallback): void;
}

const SSR_DECISION: DecisionResult = { error: 'SSR environment', action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 };

// No-op version for SSR/Node environments
const VeilProofSSR: VeilProofAPI = {
  init: () => console.warn('[VeilProof] Running in SSR environment - SDK disabled'),
  destroy: () => {},
  getSessionId: () => '',
  getSessionMeta: () => ({ sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false }),
  getDecision: (callback: DecisionCallback) => callback(SSR_DECISION),
  getToken: ((callback?: TokenCallback) => {
    const result: TokenResult = { token: null, decision: SSR_DECISION, error: 'SSR environment' };
    if (callback) { callback(result); return; }
    return Promise.resolve(result);
  }) as { (callback: TokenCallback): void; (): Promise<TokenResult> },
  getDebugSnapshot: () => ({ version: SDK_VERSION, initialized: false, debug: false, session: { id: '', meta: { sessionId: '', startTime: 0, userAgent: '', platform: '', webdriverFlag: false, hasTouch: false } }, buffer: { eventCount: 0, recentEvents: [] }, collectors: { mouse: false, click: false, keyboard: false, scroll: false, focus: false, touch: false } }),
  selfTest: (callback: SelfTestCallback) => callback({ version: SDK_VERSION, tests: [{ name: 'SSR Environment', status: 'warn', error: 'SDK disabled in SSR' }], passed: 0, failed: 0, overall: 'unknown' })
};

const VeilProof: VeilProofAPI = {
  /**
   * Initialize VeilProof SDK.
   */
  init(config: VeilProofConfig = { apiKey: '' }) {
    if (!isBrowser) {
      console.warn('[VeilProof] Running in SSR environment - SDK disabled');
      return;
    }

    if (initialized) {
      if (debug) console.warn('[VeilProof] Already initialized');
      return;
    }

    // Validate configuration
    const validation = validateConfig(config);
    if (!validation.valid) {
      const errorMsg = `[VeilProof] Configuration error: ${validation.error}. Get an API key at https://veilproof.com/dashboard`;
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
      console.log(`[VeilProof] v${SDK_VERSION} Initialized ✓`);
      console.log(`[VeilProof] Session: ${getSessionId().slice(-8)}`);
      console.log(`[VeilProof] Endpoint: ${config.endpoint}`);
      console.log('[VeilProof] Collectors: mouse, click, keyboard, scroll, focus' + ('ontouchstart' in window ? ', touch' : ''));
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
    if (debug) console.log('[VeilProof] Destroyed');
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
      VeilProofSSR.getDecision(callback);
      return;
    }

    if (!initialized) {
      callback({ error: 'VeilProof not initialized. Call init() first.', action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 });
      return;
    }

    try {
      // Get collected events
      const events = getEvents();
      const sessionMeta = getSessionMeta();
      
      if (debug) {
        console.log('[VeilProof] Getting decision...');
        console.log(`[VeilProof] Events collected: ${events.length}`);
      }

      // Extract features from events (V4 feature set)
      const features = computeFeatures(events, sessionMeta);
      
      if (debug) {
        console.log('[VeilProof] Computed features:', Object.keys(features).slice(0, 10), '...');
        console.log('[VeilProof] Total feature count:', Object.keys(features).length);
        console.log('[VeilProof] Sample feature values:', {
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
        ...fingerprint,
        // Honeypot (strategy step 7): true if a bot filled the hidden trap
        // field auto-init injects into data-veilproof forms. Decisive bot
        // signal server-side; harmlessly false for programmatic integrations
        // that don't use the honeypot.
        honeypot_triggered: isHoneypotTriggered(),
      };
      
      if (debug) {
        console.log('[VeilProof] Request body keys:', Object.keys(requestBody).slice(0, 25));
        console.log('[VeilProof] Total request body keys:', Object.keys(requestBody).length);
      }

      // Send to prediction API - use init config or default to production
      const endpoint = initConfig?.endpoint || DEFAULT_ENDPOINT;
      const apiKey = initConfig?.apiKey || '';
      
      if (!apiKey) {
        callback({ error: 'API key not provided', action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 });
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
          if (debug) console.warn('[VeilProof] Prediction request failed:', message);
          callback({ error: message, action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 });
          return;
        }

        if (debug) {
          console.log('[VeilProof] Decision received:', body);
        }
        callback(body as DecisionResult);
      })
      .catch(error => {
        console.error('[VeilProof] Prediction error:', error);
        callback({ error: (error as Error).message, action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 });
      });

    } catch (error) {
      console.error('[VeilProof] getDecision error:', error);
      callback({ error: (error as Error).message, action: 'block', risk_score: 100, behavior_score: 100, fingerprint_score: 100, confidence: 0 });
    }
  },

  /**
   * Get a verification token for the current session (wraps getDecision).
   * Pass a callback for the classic style, or call with no arguments to get
   * a Promise — both forms resolve to `{ token, decision, error? }`, where
   * `token` is the value to hand to your server for /api/siteverify.
   */
  getToken: ((callback?: TokenCallback) => {
    const run = (cb: TokenCallback) => {
      VeilProof.getDecision((decision: DecisionResult) => {
        cb({
          token: decision.verification_token || null,
          decision,
          error: decision.error,
        });
      });
    };

    if (callback) {
      run(callback);
      return;
    }
    return new Promise<TokenResult>((resolve) => run(resolve));
  }) as { (callback: TokenCallback): void; (): Promise<TokenResult> },

  /**
   * Get debug snapshot for troubleshooting
   * Returns current SDK state including buffer, session meta, and recent events
   */
  getDebugSnapshot(): DebugSnapshot {
    if (!isBrowser) {
      return VeilProofSSR.getDebugSnapshot();
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
      VeilProofSSR.selfTest(callback);
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

    // Test 2: API key check — prefer the actual init() config over the
    // legacy window.VEILPROOF_CONFIG global, which script-tag/npm callers
    // never set.
    const apiKey = initConfig?.apiKey || (window as any).VEILPROOF_CONFIG?.API_KEY;
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
    const endpoint = (window as any).VEILPROOF_CONFIG?.BACKEND_URL || initConfig?.endpoint || DEFAULT_ENDPOINT;
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
        if (debug) console.log('[VeilProof] Self-test results:', results);
        callback(results);
      })
      .catch(error => {
        results.tests.push({ name: 'Network Reachable', status: 'fail', error: (error as Error).message });
        results.failed++;
        results.overall = results.failed === 0 ? 'pass' : 'fail';
        if (debug) console.log('[VeilProof] Self-test results:', results);
        callback(results);
      });
  },
};

// Export for esbuild to handle global exposure
export default VeilProof;

// Manual global exposure for browser usage (outside of esbuild's control)
if (typeof window !== 'undefined') {
  (window as any).VeilProof = VeilProof;
  runAutoInit(VeilProof);
}
