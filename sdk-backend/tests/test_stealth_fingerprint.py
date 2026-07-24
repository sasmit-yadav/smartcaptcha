"""Unit tests for stealth-automation fingerprint scoring + CDP inconclusive policy."""
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
        automation_signals=["webdriver_undefined"],
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


def test_cdp_only_signal_is_inconclusive_not_block():
    """P0: classic CDP Runtime.enable alone must not force a block."""
    engine = RiskEngine()
    result = engine.evaluate_session(
        ml_probability=0.04,
        webdriver_flag=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0",
        has_touch=False,
        platform="Win32",
        decision_threshold=0.6,
        automation_score=85.0,  # legacy client score; server must still cap
        automation_signals=["cdp_runtime_enable"],
    )
    assert result["fingerprint_score"] < 50
    assert result["fingerprint_score"] == 35.0
    assert result["decision"] == "allow"


def test_cdp_plus_decisive_signal_still_blocks():
    engine = RiskEngine()
    result = engine.evaluate_session(
        ml_probability=0.04,
        webdriver_flag=False,
        user_agent="Mozilla/5.0",
        has_touch=False,
        platform="Win32",
        decision_threshold=0.6,
        automation_score=100.0,
        automation_signals=["cdp_runtime_enable", "webdriver_undefined"],
    )
    assert result["fingerprint_score"] >= 50
    assert result["decision"] == "block"
