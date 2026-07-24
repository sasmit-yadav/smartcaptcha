"""Unit tests for BotDetector._rule_risk_boost (neuromotor + computer-use)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from models.inference import BotDetector  # noqa: E402


@pytest.fixture
def detector(monkeypatch):
    """Construct BotDetector without loading real model artifacts."""
    det = BotDetector.__new__(BotDetector)
    det.feature_columns = ["event_count", "session_duration"]
    det.model = MagicMock()
    det.scaler = MagicMock()
    det.anomaly_forest = None
    return det


def test_humanish_features_get_little_or_no_boost(detector):
    boost = detector._rule_risk_boost(
        {
            "event_count": 120,
            "session_duration": 8,
            "key_count": 10,
            "std_iki": 45,
            "click_count": 3,
            "click_interval_std": 180,
            "mouse_event_ratio": 0.7,
            "mouse_path_efficiency": 0.72,
            "mouse_tremor_band_ratio": 0.12,
            "mouse_powerlaw_r2": 0.4,
            "movement_entropy": 1.8,
            "mouse_jerk_std": 500,
            "mouse_curvature_std": 0.8,
            "click_teleport_ratio": 0.0,
            "avg_pre_click_moves": 18,
            "inter_click_gap_cv": 0.9,
            "long_gap_ratio": 0.0,
            "min_pre_click_path": 220,
        }
    )
    assert boost < 0.15


def test_short_human_form_fill_not_boosted(detector):
    """Click → type → click nearby fields looks 'teleport-ish' but is human."""
    boost = detector._rule_risk_boost(
        {
            "event_count": 35,
            "session_duration": 12,
            "key_count": 18,
            "std_iki": 55,
            "click_count": 4,
            "click_interval_std": 400,
            "mouse_event_ratio": 0.35,
            "mouse_path_efficiency": 0.8,
            "mouse_tremor_band_ratio": 0.08,
            "mouse_powerlaw_r2": 0.3,
            "movement_entropy": 1.2,
            "mouse_jerk_std": 8000,
            "mouse_curvature_std": 0.6,
            # Sparse approaches are common when pausing then clicking a field.
            "click_teleport_ratio": 0.5,
            "avg_pre_click_moves": 2.0,
            "inter_click_gap_cv": 0.7,
            "long_gap_ratio": 0.2,
            "min_pre_click_path": 30,
        }
    )
    assert boost < 0.20


def test_vision_agent_teleport_boosts(detector):
    boost = detector._rule_risk_boost(
        {
            "event_count": 20,
            "session_duration": 6,
            "click_count": 4,
            "mouse_event_ratio": 0.1,
            "mouse_path_efficiency": 0.5,
            "click_teleport_ratio": 0.85,
            "avg_pre_click_moves": 1.0,
            "min_pre_click_path": 5,
            "inter_click_gap_cv": 0.2,
            "long_gap_ratio": 0.75,
            "mouse_tremor_band_ratio": -1,
            "mouse_powerlaw_r2": 0,
            "movement_entropy": 0,
            "mouse_jerk_std": 0,
            "mouse_curvature_std": 0,
            "std_iki": 50,
            "click_interval_std": 50,
            "key_count": 0,
        }
    )
    assert boost >= 0.28
    assert boost <= 0.65


def test_missing_tremor_with_long_path_boosts(detector):
    boost = detector._rule_risk_boost(
        {
            "event_count": 80,
            "session_duration": 5,
            "click_count": 2,
            "mouse_event_ratio": 0.8,
            "mouse_path_efficiency": 0.9,
            "mouse_tremor_band_ratio": 0.0,
            "mouse_powerlaw_r2": 0.98,
            "movement_entropy": 0.2,
            "mouse_jerk_std": 300000,
            "mouse_curvature_std": 0.1,
            "click_teleport_ratio": 0,
            "avg_pre_click_moves": 10,
            "min_pre_click_path": 100,
            "inter_click_gap_cv": 1,
            "long_gap_ratio": 0,
            "std_iki": 40,
            "click_interval_std": 80,
            "key_count": 0,
        }
    )
    assert boost >= 0.35
