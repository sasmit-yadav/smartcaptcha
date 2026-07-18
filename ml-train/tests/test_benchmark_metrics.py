"""Unit tests for the benchmark metrics (spec Step 8.3) — pure math, no DB."""
import sys
from pathlib import Path

ML_TRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_TRAIN))

from benchmarks.metrics import (  # noqa: E402
    build_row,
    realised_human_fpr,
    rows_to_markdown,
    threshold_at_human_fpr,
    wilson_interval,
)


def test_wilson_interval_basic():
    lo, hi = wilson_interval(0, 40)
    assert lo == 0.0
    assert 0.0 < hi < 0.15  # zero events on 40 samples: upper bound is small but non-zero
    lo, hi = wilson_interval(20, 40)
    assert lo < 0.5 < hi


def test_wilson_interval_empty():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_threshold_respects_fpr_budget():
    humans = [10, 12, 15, 20, 25, 30]  # 6 humans
    thr = threshold_at_human_fpr(humans, target_fpr=0.0)
    # zero-FPR threshold must sit above every human score
    assert realised_human_fpr(humans, thr) == 0.0
    assert thr > max(humans)


def test_threshold_allows_budgeted_fpr():
    humans = [10] * 90 + [95] * 10  # 10% of humans score very high
    thr = threshold_at_human_fpr(humans, target_fpr=0.10)
    assert realised_human_fpr(humans, thr) <= 0.10


def test_build_row_and_markdown():
    humans = [5, 8, 10, 12, 15, 18, 20, 22]
    personas = {
        "scripted_stealth": [60, 70, 80, 90],   # clearly bot-ish, high risk
        "browser_use": [30, 35, 40, 45],         # harder, moderate risk
    }
    row = build_row("VeriFlow (V5)", humans, personas, target_fpr=0.0)
    assert row.realised_fpr == 0.0
    by_name = {p.persona: p for p in row.personas}
    # stealth persona all above the zero-FPR threshold -> full recall
    assert by_name["scripted_stealth"].recall == 1.0
    assert 0.0 <= by_name["browser_use"].recall <= 1.0

    md = rows_to_markdown([row])
    assert "VeriFlow (V5)" in md
    assert "scripted_stealth" in md
    assert "Human FPR" in md
