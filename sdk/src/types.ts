/**
 * NextCaptcha SDK Type Definitions
 */

export interface VeriFlowConfig {
  apiKey: string;
  endpoint?: string;
  debug?: boolean;
  source?: 'demo' | 'client'; // Source of the session (demo site or customer website)
  disableTelemetry?: boolean; // Disable telemetry sending (for lightweight backends)
}

export interface SessionMeta {
  sessionId: string;
  startTime: number;
  userAgent?: string;
  platform?: string;
  webdriverFlag?: boolean;
  hasTouch?: boolean;
  source?: 'demo' | 'client'; // Source of the session
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
  action: 'allow' | 'block' | 'challenge';
  bot_probability: number;
  risk_score: number;
  confidence: number;
  risk_engine_enabled: boolean;
  behavior_score: number;
  fingerprint_score: number;
  overall_risk: number;
  error?: string;
}

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
