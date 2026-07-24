"""Unit tests for stealth-automation fingerprint scoring."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from models.risk_engine import RiskEngine  # noqa: E402


def test_spoofed_automation_score_blocks():
    engine = RiskEngine()
    result = engine.evaluate_session(
        ml_probability=0.04,  # looks "human" to the supervised model
        webdriver_flag=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0",
        has_touch=False,
        platform="Win32",
        decision_threshold=0.6,
        automation_score=100.0,
    )
    assert result["fingerprint_score"] >= 50
    assert result["decision"] == "block"


def test_clean_browser_still_allows_low_behavior():
    engine = RiskEngine()
    result = engine.evaluate_session(
        ml_probability=0.04,
        webdriver_flag=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0",
        has_touch=False,
        platform="Win32",
        decision_threshold=0.6,
        automation_score=0.0,
    )
    assert result["fingerprint_score"] == 0
    assert result["decision"] == "allow"
