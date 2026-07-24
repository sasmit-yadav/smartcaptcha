# Model Version History

> **Product status (2026-07-24):** detection stack through **P1** is documented in
> `docs/INDEX.md` / `docs/VeilProof_Status_Through_2026-07-24.md`. Next training
> wave is **P2** (Camoufox/rebrowser labeled sessions). This file remains the
> historical artifact log for shipped model packages.

## V4 (Current) - 2026-06-22

### Recovery Roadmap Implementation
**5-Stage Recovery Roadmap Completed:**
- Stage 0: Frozen baseline V2 for comparison
- Stage 1: Audit - false positive analysis, feature distributions, bot family labeling
- Stage 2: Added 3 new behavioral features (curvature std, jerk std, movement entropy)
- Stage 3: Telemetry V2 - webdriver flag, hover duration, overshoot ratio
- Stage 4: Training methodology fixes (bot family split, FPR optimization, tiered thresholds)
- Stage 5: Risk Engine architecture (Behavior + Fingerprint + Challenge)

### Dataset
- **Total Sessions**: 173 (141 bot + 32 human)
- **Training Methodology**: Bot family split (eliminates evaluation leakage)
  - Train families: instant_slow, instant_medium
  - Test families: instant_fast, short_slow
- **Training Split**: 77 train / 26 validation / 70 test
- **Data Sources**: Same as V2, but with V4 features extracted

### Features (48 dimensions)
**V1 Base Features (17)**: avg_mouse_vel, std_mouse_vel, max_mouse_vel, total_distance, avg_angle_change, click_count, avg_click_interval, avg_iki, std_iki, avg_hold, scroll_count, avg_scroll_vel, session_duration, event_count, key_count, mouse_move_count, scroll_count

**V2 Additions (27)**: mouse_vel_p10, mouse_vel_p50, mouse_vel_p90, mouse_accel_mean, mouse_accel_std, mouse_accel_max, mouse_angle_std, mouse_angle_p90, mouse_path_efficiency, mouse_idle_gap_count, mouse_event_ratio, click_interval_std, click_interval_min, click_interval_p90, double_click_count, iki_p10, iki_p50, iki_p90, hold_std, hold_p90, backspace_count, scroll_vel_std, scroll_rev_count, scroll_pause_count, focus_event_count, touch_event_count, event_rate, pause_count, pause_ratio

**V3 Additions (3)**: mouse_curvature_std, mouse_jerk_std, movement_entropy

**V4 Additions (5)**: avg_hover_duration, hover_duration_std, avg_overshoot_ratio, overshoot_ratio_std, webdriver_flag

### Model
- **Selected Model**: Random Forest
- **Threshold**: 0.24 (tuned for FPR < 1%)
- **Test Metrics**: F1=0.9831, Precision=1.0, Recall=0.9667, FPR=0.0%
- **Top Features**: mouse_path_efficiency (9.4%), avg_mouse_vel (8.4%), std_mouse_vel (8.2%), session_duration (8.0%), mouse_jerk_std (7.3%)

### Risk Engine (Stage 5)
- **Architecture**: Multi-factor scoring (Behavior + Fingerprint + Challenge)
- **Weights**: Behavior 50%, Fingerprint 30%, Challenge 20%
- **Tiered Thresholds**: Allow < 25, Challenge 25-80, Block > 80
- **Fingerprint Signals**: webdriver flag, user agent analysis, touch detection, platform analysis
- **Challenge Scoring**: Time-based analysis, accuracy analysis

### Artifacts
**Location**: `ml/models/artifacts/`
- `random_forest_20260622_133850.pkl` - Model file
- `scaler_20260622_133850.pkl` - Feature scaler
- `random_forest_metrics_20260622_133850.json` - Performance metrics
- `random_forest_feature_importance_20260622_133850.csv` - Feature importance
- `random_forest_metadata_20260622_133850.json` - Model metadata with V4 parameters
- `model_comparison_20260622_133856.json` - Model comparison results

### Key Improvements over V2
1. **Eliminated evaluation leakage** via bot family-aware train/test split
2. **Zero false positive rate** achieved on test set (vs potential FPs in V2)
3. **Robust behavioral features** (curvature, jerk, entropy) against stealth bots
4. **V2 telemetry signals** (webdriver flag, hover duration, overshoot ratio)
5. **Risk Engine architecture** for production-grade multi-factor scoring
6. **Tiered threshold tuning** for better UX (allow/challenge/block instead of binary)

### Baseline Comparison
**Baseline V2 Issues:**
- Perfect metrics (F1=1.0) suspicious due to evaluation leakage
- Same bot families in train/test causing overfitting
- High-separation features (event_count, session_duration) causing shortcut learning
- Only behavioral scoring, missing fingerprint/challenge components

**V4 Solutions:**
- Bot family split eliminates leakage
- 0% FPR on unseen bot families
- New behavioral features capture movement patterns beyond shortcuts
- Multi-factor Risk Engine for comprehensive scoring
- Tiered thresholds for better user experience

---

## V2 (Baseline) - 2026-06-19

### Dataset
- **Total Sessions**: 183 (141 bot + 42 human)
- **Training Split**: 103 train / 35 validation / 35 test
- **Data Sources**:
  - Original human sessions: 33
  - New human sessions: 9
  - Original bot sessions: 100
  - New bot sessions (demo-site): 41
    - instant_bot: 5 sessions
    - linear_bot: 5 sessions
    - timed_bot: 5 sessions
    - smart_bot: 5 sessions
    - adversarial_bot: 5 sessions
    - multi_page_bot: 5 sessions
    - aggressive_bot: 0 (failed on demo-site)
    - stealth_bot: 0 (reserved for testing)

### Features (44 dimensions)
**V1 Features (14)**: avg_mouse_vel, max_mouse_vel, std_mouse_vel, avg_angle_change, avg_click_interval, std_click_interval, avg_iki, std_iki, event_count, session_duration, key_count, click_count, mouse_move_count, scroll_count

**V2 Additions (30 new)**:
- **Percentiles**: mouse_vel_p10, mouse_vel_p50, mouse_vel_p90, click_interval_p10, click_interval_p50, click_interval_p90, iki_p10, iki_p50, iki_p90, hold_p10, hold_p50, hold_p90
- **Acceleration**: mouse_accel_mean, mouse_accel_std, mouse_accel_max
- **Path Efficiency**: mouse_path_efficiency (straight-line distance / total distance)
- **Pauses**: mouse_idle_gap_count, pause_count
- **Timing Distribution**: click_interval_std, hold_std
- **Edits**: backspace_count
- **Scroll Behavior**: scroll_vel_std, scroll_rev_count, scroll_pause_count
- **Focus**: focus_event_count
- **Clicks**: double_click_count
- **Event Rate**: event_rate (events per second)

### Model
- **Selected Model**: Random Forest
- **Threshold**: 0.52 (tuned on validation set)
- **Test Metrics**: F1=1.0000, ROC-AUC=1.0000
- **Top Features**: std_mouse_vel (13.9%), mouse_accel_std (10.1%), session_duration (10.0%)

### Artifacts
**Location**: `ml/models/artifacts/v2/`
- `random_forest_20260619_210124.pkl` - Model file
- `scaler_20260619_210124.pkl` - Feature scaler
- `random_forest_metrics_20260619_210124.json` - Performance metrics
- `random_forest_feature_importance_20260619_210124.csv` - Feature importance
- `random_forest_metadata_20260619_210124.json` - Model metadata
- `model_comparison_20260619_210129.json` - Model comparison results

### Evaluation
- **Stealth Bot (testing-website)**: DETECTED
  - Bot probability: 70.0%
  - Risk score: 70/100
  - Confidence: 63.4%

### Key Improvements over V1
1. Target-aware bot code (demo-site for training, testing-website for evaluation)
2. API schema compatibility fix (sessionId in meta object)
3. Multi-page bot coverage for diverse training data
4. 30 additional behavioral features capturing distribution and sequence patterns
5. Expanded dataset with 41 new bot sessions across 6 bot types
6. Threshold tuning instead of hardcoded 0.50

---

## V1 - 2026-06-19 (Initial)

### Dataset
- **Total Sessions**: 142 (100 bot + 33 human + 9 unlabeled)
- **Features Extracted**: 133 sessions
- **Data Sources**: Original human sessions + basic bot types

### Features (14 dimensions)
avg_mouse_vel, max_mouse_vel, std_mouse_vel, avg_angle_change, avg_click_interval, std_click_interval, avg_iki, std_iki, event_count, session_duration, key_count, click_count, mouse_move_count, scroll_count

### Model
- **Selected Model**: Random Forest
- **Threshold**: 0.50 (hardcoded)
- **Test Metrics**: F1=1.0000 (on small test set)

### Artifacts
**Location**: `ml/models/artifacts/v1/`
- `random_forest_20260615_193406.pkl` - Model file
- `random_forest_20260619_144835.pkl` - Intermediate model file
- `scaler_20260615_193406.pkl` - Feature scaler
- `random_forest_metrics_20260615_193406.json` - Performance metrics
- `random_forest_feature_importance_20260615_193406.csv` - Feature importance
- `model_comparison_20260615_193410.json` - Model comparison results

### Issues
- Human-like bot (stealth_bot) could bypass detection
- Limited feature set (only aggregate statistics)
- Hardcoded threshold
- Small dataset
- No adversarial training data

---

## Version Naming Convention

### Model Files
- `{model_type}_{YYYYMMDD_HHMMSS}.pkl` - Trained model
- `scaler_{YYYYMMDD_HHMMSS}.pkl` - Feature scaler
- `{model_type}_metrics_{YYYYMMDD_HHMMSS}.json` - Performance metrics
- `{model_type}_feature_importance_{YYYYMMDD_HHMMSS}.csv` - Feature importance
- `{model_type}_metadata_{YYYYMMDD_HHMMSS}.json` - Model metadata
- `model_comparison_{YYYYMMDD_HHMMSS}.json` - Model comparison results

### Feature Versions
- V1: 14 features (basic aggregates)
- V2: 44 features (aggregates + percentiles + distributions + sequences)

### Dataset Versions
- V1: 142 sessions (100 bot + 33 human)
- V2: 183 sessions (141 bot + 42 human)
