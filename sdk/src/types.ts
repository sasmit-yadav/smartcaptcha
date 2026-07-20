/**
 * VeilProof SDK Type Definitions
 */

export interface VeilProofConfig {
  apiKey: string;
  endpoint?: string;
  debug?: boolean;
  source?: 'demo' | 'client' | 'script-tag'; // Source of the session (demo site, customer website, or script-tag auto-init)
  disableTelemetry?: boolean; // Disable telemetry sending (for lightweight backends)
}

export interface SessionMeta {
  sessionId: string;
  startTime: number;
  userAgent?: string;
  platform?: string;
  webdriverFlag?: boolean;
  hasTouch?: boolean;
  source?: 'demo' | 'client' | 'script-tag'; // Source of the session
}

export interface TelemetryEvent {
  type: string;
  t: number;
  x?: number;
  y?: number;
  key?: string;
  scrollY?: number;
  target?: string;
  [key: string]: any; // Allow additional properties for collector-specific data
}

export interface FeatureVector {
  // Mouse features
  mouse_count: number;
  mouse_vel_mean: number;
  mouse_vel_std: number;
  mouse_vel_max: number;
  mouse_accel_mean: number;
  mouse_accel_std: number;
  mouse_accel_max: number;
  mouse_angle_std: number;
  mouse_angle_p90: number;
  mouse_path_efficiency: number;
  mouse_idle_gap_count: number;
  mouse_event_ratio: number;
  
  // Click features
  click_count: number;
  click_interval_std: number;
  click_interval_min: number;
  click_interval_p90: number;
  double_click_count: number;
  
  // Keyboard features
  key_count: number;
  iki_p10: number;
  iki_p50: number;
  iki_p90: number;
  hold_std: number;
  hold_p90: number;
  backspace_count: number;
  
  // Scroll features
  scroll_count: number;
  avg_scroll_vel: number;
  scroll_vel_std: number;
  scroll_rev_count: number;
  scroll_pause_count: number;
  
  // Focus features
  focus_event_count: number;
  
  // Touch features
  touch_event_count: number;
  
  // Session features
  session_duration: number;
  event_count: number;
  event_rate: number;
  pause_count: number;
  pause_ratio: number;
  
  // Advanced features
  mouse_vel_p10: number;
  mouse_vel_p50: number;
  mouse_vel_p90: number;
  mouse_curvature_std: number;
  mouse_jerk_std: number;
  movement_entropy: number;
  avg_hover_duration: number;
  hover_duration_std: number;
  avg_overshoot_ratio: number;
  overshoot_ratio_std: number;
}

export interface FingerprintData {
  webdriver_flag: boolean;
  user_agent: string;
  has_touch: boolean;
  platform: string;
}

export interface DecisionResult {
  /** Binary verdict — there is no 'challenge' tier; nothing in the product implements a challenge flow. */
  action: 'allow' | 'block';
  /** Combined 0-100 risk score (the same number the API calls risk_score). */
  risk_score: number;
  /** 0-100, VeilProof's behavioral risk signal. */
  behavior_score: number;
  /** 0-100, VeilProof's device/environment risk signal. */
  fingerprint_score: number;
  /** 0-1, how far risk_score sits from the 50-point decision boundary. */
  confidence: number;
  error?: string;
  /** Short-lived, single-use token for server-side /api/siteverify redemption. */
  verification_token?: string;
}

export interface TokenResult {
  token: string | null;
  decision: DecisionResult;
  error?: string;
}

export type TokenCallback = (result: TokenResult) => void;

export interface DebugSnapshot {
  version: string;
  initialized: boolean;
  debug: boolean;
  session: {
    id: string;
    meta: SessionMeta;
  };
  buffer: {
    eventCount: number;
    recentEvents: TelemetryEvent[];
  };
  collectors: {
    mouse: boolean;
    click: boolean;
    keyboard: boolean;
    scroll: boolean;
    focus: boolean;
    touch: boolean;
  };
}

export interface SelfTestResult {
  version: string;
  tests: Array<{
    name: string;
    status: 'pass' | 'fail' | 'warn';
    error?: string;
    count?: number;
  }>;
  passed: number;
  failed: number;
  overall: 'pass' | 'fail' | 'unknown';
}

export type DecisionCallback = (result: DecisionResult) => void;
export type SelfTestCallback = (result: SelfTestResult) => void;
