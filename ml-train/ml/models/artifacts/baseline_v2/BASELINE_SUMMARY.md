# Baseline V2 - Frozen Snapshot

**Date**: 2026-06-22  
**Purpose**: Reference point before implementing recovery roadmap

## Current State

### Model Information
- **Model Type**: Random Forest
- **Feature Version**: V2 (44 features)
- **Decision Threshold**: 0.52
- **Created**: 2026-06-19T21:01:24

### Dataset
- **Total Sessions**: 183 (141 bot + 42 human)
- **Training Split**: 103 train / 35 validation / 35 test
- **Data Sources**:
  - Original human sessions: 33
  - New human sessions: 9
  - Original bot sessions: 100
  - New bot sessions (demo-site): 41

### Current Metrics (Test Set)
- **Precision**: 1.0000
- **Recall**: 1.0000
- **F1-Score**: 1.0000
- **ROC-AUC**: 1.0000
- **Confusion Matrix**: 
  - True Negatives: 6
  - False Positives: 0
  - False Negatives: 0
  - True Positives: 29

### Cross-Validation Scores
- **Precision**: 0.9789 ± 0.0421
- **Recall**: 0.9882 ± 0.0235
- **F1**: 0.9828 ± 0.0225
- **ROC-AUC**: 0.9941 ± 0.0118

### Feature List (44 dimensions)
**V1 Base Features (17)**:
- avg_mouse_vel, std_mouse_vel, max_mouse_vel, total_distance
- avg_angle_change, click_count, avg_click_interval
- avg_iki, std_iki, avg_hold, scroll_count, avg_scroll_vel
- session_duration, event_count

**V2 Additions (27)**:
- mouse_vel_p10, mouse_vel_p50, mouse_vel_p90
- mouse_accel_mean, mouse_accel_std, mouse_accel_max
- mouse_angle_std, mouse_angle_p90
- mouse_path_efficiency, mouse_idle_gap_count, mouse_event_ratio
- click_interval_std, click_interval_min, click_interval_p90
- double_click_count, key_count
- iki_p10, iki_p50, iki_p90
- hold_std, hold_p90, backspace_count
- scroll_vel_std, scroll_rev_count, scroll_pause_count
- focus_event_count, touch_event_count, event_rate
- pause_count, pause_ratio

### Top Features (by importance)
1. std_mouse_vel (13.9%)
2. mouse_accel_std (10.1%)
3. session_duration (10.0%)

## Known Issues
1. **Perfect metrics suspicious**: F1=1.0, ROC-AUC=1.0 suggests evaluation leakage
2. **False positives**: Real humans being predicted as bots in production
3. **Limited human diversity**: Only 42 human sessions vs 141 bot sessions
4. **Weak features**: Mostly global averages that bots can mimic
5. **Potential bot family leakage**: Same bot types may appear in train/test

## Artifacts Location
- Model: `random_forest_20260619_210124.pkl`
- Scaler: `scaler_20260619_210124.pkl`
- Metrics: `random_forest_metrics_20260619_210124.json`
- Feature Importance: `random_forest_feature_importance_20260619_210124.csv`
- Metadata: `random_forest_metadata_20260619_210124.json`
- Model Comparison: `model_comparison_20260619_210129.json`

## Next Steps
This baseline serves as the reference point for the 5-stage recovery roadmap:
- Stage 1: Audit current model (false positive analysis, feature distributions, bot family labeling)
- Stage 2: Upgrade features (add 5 new behavioral features)
- Stage 3: Telemetry V2 (add webdriver flag, hover duration, overshoot ratio)
- Stage 4: Fix training methodology (bot family split, false positive optimization, threshold tuning)
- Stage 5: Upgrade to Risk Engine architecture
