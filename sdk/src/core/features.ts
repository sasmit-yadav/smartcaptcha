/**
 * Feature Computation — computes V4 features from raw telemetry events.
 * Computes: hover duration, overshoot ratio, curvature, jerk, entropy
 */

import type { TelemetryEvent } from '../types.js';

interface FeatureVector {
  // Basic features (already computed)
  avg_mouse_vel: number;
  std_mouse_vel: number;
  max_mouse_vel: number;
  total_distance: number;
  avg_angle_change: number;
  click_count: number;
  avg_click_interval: number;
  avg_iki: number;
  std_iki: number;
  avg_hold: number;
  scroll_count: number;
  avg_scroll_vel: number;
  session_duration: number;
  event_count: number;
  
  // V2 features
  mouse_vel_p10: number;
  mouse_vel_p50: number;
  mouse_vel_p90: number;
  mouse_accel_mean: number;
  mouse_accel_std: number;
  mouse_accel_max: number;
  mouse_angle_std: number;
  mouse_angle_p90: number;
  mouse_path_efficiency: number;
  mouse_idle_gap_count: number;
  mouse_event_ratio: number;
  click_interval_std: number;
  click_interval_min: number;
  click_interval_p90: number;
  double_click_count: number;
  key_count: number;
  iki_p10: number;
  iki_p50: number;
  iki_p90: number;
  hold_std: number;
  hold_p90: number;
  backspace_count: number;
  scroll_vel_std: number;
  scroll_rev_count: number;
  scroll_pause_count: number;
  focus_event_count: number;
  touch_event_count: number;
  event_rate: number;
  pause_count: number;
  pause_ratio: number;
  
  // V3 features
  mouse_curvature_std: number;
  mouse_jerk_std: number;
  movement_entropy: number;
  
  // V4 features
  avg_hover_duration: number;
  hover_duration_std: number;
  avg_overshoot_ratio: number;
  overshoot_ratio_std: number;
  webdriver_flag: boolean;
}

export function computeFeatures(events: TelemetryEvent[], sessionMeta: any): FeatureVector {
  const startTime = sessionMeta.startTime || Date.now();
  const endTime = Date.now();
  const sessionDuration = (endTime - startTime) / 1000; // seconds
  const eventCount = events.length;
  
  // Separate events by type
  const mouseEvents = events.filter(e => e.type === 'mm');
  const clickEvents = events.filter(e => e.type === 'cl');
  const keyEvents = events.filter(e => e.type === 'kd' || e.type === 'ku');
  const scrollEvents = events.filter(e => e.type === 'sc');
  const focusEvents = events.filter(e => e.type === 'fo');
  const touchEvents = events.filter(e => e.type === 'to');
  
  // Basic mouse features
  const velocities = mouseEvents.map(e => e.vel || 0);
  const distances = mouseEvents.map(e => e.dist || 0);
  const angles = mouseEvents.map(e => e.ang || 0).filter(a => a !== null);
  const totalDistance = distances.reduce((a, b) => a + b, 0);
  
  // Compute statistics
  const avgMouseVel = velocities.length > 0 ? velocities.reduce((a, b) => a + b, 0) / velocities.length : 0;
  const stdMouseVel = computeStd(velocities);
  const maxMouseVel = velocities.length > 0 ? Math.max(...velocities) : 0;
  const avgAngleChange = angles.length > 0 ? angles.reduce((a, b) => a + b, 0) / angles.length : 0;
  
  // Percentiles
  const mouseVelP10 = computePercentile(velocities, 10);
  const mouseVelP50 = computePercentile(velocities, 50);
  const mouseVelP90 = computePercentile(velocities, 90);
  
  // Acceleration (change in velocity)
  const accelerations = [];
  for (let i = 1; i < velocities.length; i++) {
    const dt = mouseEvents[i].t - mouseEvents[i-1].t;
    if (dt > 0) {
      accelerations.push((velocities[i] - velocities[i-1]) / dt * 1000);
    }
  }
  const mouseAccelMean = accelerations.length > 0 ? accelerations.reduce((a, b) => a + b, 0) / accelerations.length : 0;
  const mouseAccelStd = computeStd(accelerations);
  const mouseAccelMax = accelerations.length > 0 ? Math.max(...accelerations) : 0;
  
  // Angle statistics
  const mouseAngleStd = computeStd(angles);
  const mouseAngleP90 = computePercentile(angles, 90);
  
  // Path efficiency (straight line distance vs actual distance)
  const mousePathEfficiency = mouseEvents.length >= 2 ? 
    computePathEfficiency(mouseEvents) : 1;
  
  // Idle gaps (periods with no mouse movement)
  const mouseIdleGapCount = computeIdleGaps(mouseEvents);
  const mouseEventRatio = eventCount > 0 ? mouseEvents.length / eventCount : 0;
  
  // Click features
  const clickCount = clickEvents.length;
  const clickIntervals = [];
  for (let i = 1; i < clickEvents.length; i++) {
    clickIntervals.push(clickEvents[i].t - clickEvents[i-1].t);
  }
  const avgClickInterval = clickIntervals.length > 0 ? clickIntervals.reduce((a, b) => a + b, 0) / clickIntervals.length : 0;
  const clickIntervalStd = computeStd(clickIntervals);
  const clickIntervalMin = clickIntervals.length > 0 ? Math.min(...clickIntervals) : 0;
  const clickIntervalP90 = computePercentile(clickIntervals, 90);
  
  // Double clicks (clicks within 300ms)
  const doubleClickCount = clickIntervals.filter(i => i < 300).length;
  
  // Key features
  const keyCount = keyEvents.length;
  const keyDownEvents = keyEvents.filter(e => e.type === 'kd');
  const keyUpEvents = keyEvents.filter(e => e.type === 'ku');
  
  // IKI (Inter-Key Interval)
  const ikiIntervals = [];
  for (let i = 1; i < keyDownEvents.length; i++) {
    ikiIntervals.push(keyDownEvents[i].t - keyDownEvents[i-1].t);
  }
  const avgIki = ikiIntervals.length > 0 ? ikiIntervals.reduce((a, b) => a + b, 0) / ikiIntervals.length : 0;
  const stdIki = computeStd(ikiIntervals);
  const ikiP10 = computePercentile(ikiIntervals, 10);
  const ikiP50 = computePercentile(ikiIntervals, 50);
  const ikiP90 = computePercentile(ikiIntervals, 90);
  
  // Key hold duration
  const holdDurations = [];
  for (const kd of keyDownEvents) {
    const ku = keyUpEvents.find(k => k.k === kd.k && k.t > kd.t);
    if (ku) {
      holdDurations.push(ku.t - kd.t);
    }
  }
  const avgHold = holdDurations.length > 0 ? holdDurations.reduce((a, b) => a + b, 0) / holdDurations.length : 0;
  const holdStd = computeStd(holdDurations);
  const holdP90 = computePercentile(holdDurations, 90);
  
  // Backspace count
  const backspaceCount = keyDownEvents.filter(e => e.k === 'Backspace').length;
  
  // Scroll features
  const scrollCount = scrollEvents.length;
  const scrollVelocities = scrollEvents.map(e => e.vel || 0);
  const avgScrollVel = scrollVelocities.length > 0 ? scrollVelocities.reduce((a, b) => a + b, 0) / scrollVelocities.length : 0;
  const scrollVelStd = computeStd(scrollVelocities);
  const scrollRevCount = scrollEvents.filter(e => (e.dy || 0) > 0).length;
  const scrollPauseCount = computeScrollPauses(scrollEvents);
  
  // Focus and touch events
  const focusEventCount = focusEvents.length;
  const touchEventCount = touchEvents.length;
  
  // Event rate and pauses
  const eventRate = sessionDuration > 0 ? eventCount / sessionDuration : 0;
  const pauseCount = computePauseCount(events);
  const pauseRatio = eventCount > 0 ? pauseCount / eventCount : 0;
  
  // V3: Curvature, Jerk, Entropy
  const mouseCurvatureStd = computeCurvatureStd(mouseEvents);
  const mouseJerkStd = computeJerkStd(mouseEvents);
  const movementEntropy = computeMovementEntropy(mouseEvents);
  
  // V4: Hover duration and overshoot ratio
  const hoverDurations = computeHoverDurations(mouseEvents);
  const avgHoverDuration = hoverDurations.length > 0 ? hoverDurations.reduce((a, b) => a + b, 0) / hoverDurations.length : 0;
  const hoverDurationStd = computeStd(hoverDurations);
  
  const overshootRatios = computeOvershootRatios(mouseEvents, clickEvents);
  const avgOvershootRatio = overshootRatios.length > 0 ? overshootRatios.reduce((a, b) => a + b, 0) / overshootRatios.length : 0;
  const overshootRatioStd = computeStd(overshootRatios);
  
  return {
    // Basic
    avg_mouse_vel: avgMouseVel,
    std_mouse_vel: stdMouseVel,
    max_mouse_vel: maxMouseVel,
    total_distance: totalDistance,
    avg_angle_change: avgAngleChange,
    click_count: clickCount,
    avg_click_interval: avgClickInterval,
    avg_iki: avgIki,
    std_iki: stdIki,
    avg_hold: avgHold,
    scroll_count: scrollCount,
    avg_scroll_vel: avgScrollVel,
    session_duration: sessionDuration,
    event_count: eventCount,
    
    // V2
    mouse_vel_p10: mouseVelP10,
    mouse_vel_p50: mouseVelP50,
    mouse_vel_p90: mouseVelP90,
    mouse_accel_mean: mouseAccelMean,
    mouse_accel_std: mouseAccelStd,
    mouse_accel_max: mouseAccelMax,
    mouse_angle_std: mouseAngleStd,
    mouse_angle_p90: mouseAngleP90,
    mouse_path_efficiency: mousePathEfficiency,
    mouse_idle_gap_count: mouseIdleGapCount,
    mouse_event_ratio: mouseEventRatio,
    click_interval_std: clickIntervalStd,
    click_interval_min: clickIntervalMin,
    click_interval_p90: clickIntervalP90,
    double_click_count: doubleClickCount,
    key_count: keyCount,
    iki_p10: ikiP10,
    iki_p50: ikiP50,
    iki_p90: ikiP90,
    hold_std: holdStd,
    hold_p90: holdP90,
    backspace_count: backspaceCount,
    scroll_vel_std: scrollVelStd,
    scroll_rev_count: scrollRevCount,
    scroll_pause_count: scrollPauseCount,
    focus_event_count: focusEventCount,
    touch_event_count: touchEventCount,
    event_rate: eventRate,
    pause_count: pauseCount,
    pause_ratio: pauseRatio,
    
    // V3
    mouse_curvature_std: mouseCurvatureStd,
    mouse_jerk_std: mouseJerkStd,
    movement_entropy: movementEntropy,
    
    // V4
    avg_hover_duration: avgHoverDuration,
    hover_duration_std: hoverDurationStd,
    avg_overshoot_ratio: avgOvershootRatio,
    overshoot_ratio_std: overshootRatioStd,
    webdriver_flag: sessionMeta.webdriverFlag || false,
  };
}

// Helper functions
function computeStd(values: number[]): number {
  if (values.length === 0) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function computePercentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)] || 0;
}

function computePathEfficiency(events: any[]): number {
  if (events.length < 2) return 1;
  const start = events[0];
  const end = events[events.length - 1];
  const straightDist = Math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2);
  const actualDist = events.reduce((sum, e) => sum + (e.dist || 0), 0);
  return actualDist > 0 ? straightDist / actualDist : 1;
}

function computeIdleGaps(events: any[]): number {
  let gaps = 0;
  let lastTime = 0;
  for (const e of events) {
    if (lastTime > 0 && e.t - lastTime > 200) {
      gaps++;
    }
    lastTime = e.t;
  }
  return gaps;
}

function computeScrollPauses(events: any[]): number {
  let pauses = 0;
  let lastTime = 0;
  for (const e of events) {
    if (lastTime > 0 && e.t - lastTime > 300) {
      pauses++;
    }
    lastTime = e.t;
  }
  return pauses;
}

function computePauseCount(events: any[]): number {
  let pauses = 0;
  let lastTime = 0;
  for (const e of events) {
    if (lastTime > 0 && e.t - lastTime > 500) {
      pauses++;
    }
    lastTime = e.t;
  }
  return pauses;
}

function computeCurvatureStd(events: any[]): number {
  if (events.length < 3) return 0;
  const curvatures = [];
  for (let i = 1; i < events.length - 1; i++) {
    const prev = events[i - 1];
    const curr = events[i];
    const next = events[i + 1];
    
    const v1x = curr.x - prev.x;
    const v1y = curr.y - prev.y;
    const v2x = next.x - curr.x;
    const v2y = next.y - curr.y;
    
    const cross = v1x * v2y - v1y * v2x;
    const dot = v1x * v2x + v1y * v2y;
    const angle = Math.abs(Math.atan2(cross, dot));
    curvatures.push(angle);
  }
  return computeStd(curvatures);
}

function computeJerkStd(events: any[]): number {
  if (events.length < 3) return 0;
  const jerks = [];
  for (let i = 2; i < events.length; i++) {
    const dt1 = events[i-1].t - events[i-2].t;
    const dt2 = events[i].t - events[i-1].t;
    if (dt1 > 0 && dt2 > 0) {
      const a1 = (events[i-1].vel - events[i-2].vel) / dt1 * 1000;
      const a2 = (events[i].vel - events[i-1].vel) / dt2 * 1000;
      const jerk = (a2 - a1) / ((dt1 + dt2) / 2) * 1000;
      jerks.push(jerk);
    }
  }
  return computeStd(jerks);
}

function computeMovementEntropy(events: any[]): number {
  if (events.length < 10) return 0;
  // Compute entropy of movement directions
  const directions = [];
  for (let i = 1; i < events.length; i++) {
    const dx = events[i].x - events[i-1].x;
    const dy = events[i].y - events[i-1].y;
    if (dx !== 0 || dy !== 0) {
      const angle = Math.atan2(dy, dx);
      directions.push(angle);
    }
  }
  
  if (directions.length === 0) return 0;
  
  // Bin directions into 8 bins
  const bins = new Array(8).fill(0);
  for (const angle of directions) {
    const bin = Math.floor(((angle + Math.PI) / (2 * Math.PI)) * 8) % 8;
    bins[bin]++;
  }
  
  // Compute entropy
  const total = directions.length;
  let entropy = 0;
  for (const count of bins) {
    if (count > 0) {
      const p = count / total;
      entropy -= p * Math.log2(p);
    }
  }
  
  return entropy;
}

function computeHoverDurations(mouseEvents: any[]): number[] {
  // Simplified: treat periods of low velocity as hovers
  const hoverDurations: number[] = [];
  let hoverStart = 0;
  let isHovering = false;
  
  for (const e of mouseEvents) {
    if (e.vel < 5 && !isHovering) {
      hoverStart = e.t;
      isHovering = true;
    } else if (e.vel >= 10 && isHovering) {
      hoverDurations.push(e.t - hoverStart);
      isHovering = false;
    }
  }
  
  return hoverDurations;
}

function computeOvershootRatios(mouseEvents: any[], clickEvents: any[]): number[] {
  const ratios: number[] = [];
  
  for (const click of clickEvents) {
    // Find mouse events around the click
    const nearby = mouseEvents.filter(e => Math.abs(e.t - click.t) < 200);
    
    if (nearby.length >= 2) {
      const beforeClick = nearby.filter(e => e.t < click.t);
      const afterClick = nearby.filter(e => e.t > click.t);
      
      if (beforeClick.length > 0 && afterClick.length > 0) {
        const lastBefore = beforeClick[beforeClick.length - 1];
        const firstAfter = afterClick[0];
        
        // Distance from click to next movement
        const overshoot = Math.sqrt(
          (firstAfter.x - click.x) ** 2 + (firstAfter.y - click.y) ** 2
        );
        
        // Distance traveled to click
        const approachDist = Math.sqrt(
          (click.x - lastBefore.x) ** 2 + (click.y - lastBefore.y) ** 2
        );
        
        if (approachDist > 0) {
          ratios.push(overshoot / approachDist);
        }
      }
    }
  }
  
  return ratios;
}
