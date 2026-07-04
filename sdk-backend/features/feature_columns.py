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

FEATURE_COLUMNS = V4_FEATURE_COLUMNS
