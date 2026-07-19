"""Shared feature definitions for training, extraction, and inference."""

LEGACY_FEATURE_COLUMNS = [
    "avg_mouse_vel",
    "std_mouse_vel",
    "max_mouse_vel",
    "total_distance",
    "avg_angle_change",
    "click_count",
    "avg_click_interval",
    "avg_iki",
    "std_iki",
    "avg_hold",
    "scroll_count",
    "avg_scroll_vel",
    "session_duration",
    "event_count",
]

V2_FEATURE_COLUMNS = LEGACY_FEATURE_COLUMNS + [
    "mouse_vel_p10",
    "mouse_vel_p50",
    "mouse_vel_p90",
    "mouse_accel_mean",
    "mouse_accel_std",
    "mouse_accel_max",
    "mouse_angle_std",
    "mouse_angle_p90",
    "mouse_path_efficiency",
    "mouse_idle_gap_count",
    "mouse_event_ratio",
    "click_interval_std",
    "click_interval_min",
    "click_interval_p90",
    "double_click_count",
    "key_count",
    "iki_p10",
    "iki_p50",
    "iki_p90",
    "hold_std",
    "hold_p90",
    "backspace_count",
    "scroll_vel_std",
    "scroll_rev_count",
    "scroll_pause_count",
    "focus_event_count",
    "touch_event_count",
    "event_rate",
    "pause_count",
    "pause_ratio",
]

V3_FEATURE_COLUMNS = V2_FEATURE_COLUMNS + [
    "mouse_curvature_std",
    "mouse_jerk_std",
    "movement_entropy",
]

V4_FEATURE_COLUMNS = V3_FEATURE_COLUMNS + [
    "avg_hover_duration",
    "hover_duration_std",
    "avg_overshoot_ratio",
    "overshoot_ratio_std",
    "webdriver_flag",
]

# V5 = V4 + hard-to-fake neuromotor features (STEP3_STEP8_IMPLEMENTATION_SPEC.md).
# Complete: "V5a" (3.2 power-law + 3.4 keystroke, robust at 20 Hz) plus "V5b"
# (3.1 sampling upgrade + 3.3 tremor, gated on measured pointer sample rate).
# mouse_tremor_band_ratio/mouse_tremor_peak_freq are computed CLIENT-SIDE ONLY
# from a raw high-rate pointermove ring buffer the server never sees (spec
# §3.5: "you don't store raw coalesced samples server-side") — the offline
# feature_extractor.py cannot recompute them from stored `events` and emits
# the -1 "unavailable" sentinel for historical rows, same as the client does
# when the measured sample rate is under the 40 Hz Nyquist guard.
V5_FEATURE_COLUMNS = V4_FEATURE_COLUMNS + [
    "mouse_powerlaw_beta",
    "mouse_powerlaw_r2",
    "key_dwell_cv",
    "key_flight_cv",
    "key_digraph_std",
    "mouse_tremor_band_ratio",
    "mouse_tremor_peak_freq",
]

FEATURE_COLUMNS = V5_FEATURE_COLUMNS
