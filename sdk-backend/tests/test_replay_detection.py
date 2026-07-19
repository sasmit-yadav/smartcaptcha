"""Unit tests for replay-trace detection (strategy doc Part D.2)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import core.replay_detection as replay_detection  # noqa: E402
from core.replay_detection import record_and_score, reset  # noqa: E402


def setup_function():
    reset()


def _human_like_vector(seed: float) -> list:
    # 59 dims, small natural variation per "session" — simulates real
    # session-to-session motor variability.
    return [seed + i * 0.01 for i in range(59)]


def test_first_session_has_no_comparison():
    r = record_and_score("proj-1", "session-a", _human_like_vector(0.0))
    assert r.duplicate_score == 0.0
    assert r.nearest_distance is None
    assert r.compared_against == 0


def test_two_naturally_varying_humans_score_low():
    record_and_score("proj-1", "session-a", _human_like_vector(0.0))
    r = record_and_score("proj-1", "session-b", _human_like_vector(5.0))
    assert r.duplicate_score == 0.0


def test_exact_replayed_vector_scores_high():
    vector = _human_like_vector(1.0)
    record_and_score("proj-1", "session-a", vector)
    r = record_and_score("proj-1", "session-b", list(vector))  # byte-identical replay
    assert r.duplicate_score == 100.0
    assert r.nearest_session_id == "session-a"


def test_near_identical_vector_scores_between_soft_and_hard():
    vector = _human_like_vector(1.0)
    record_and_score("proj-1", "session-a", vector)
    # Perturb slightly less than the hard threshold's worth of distance
    nudged = [v + 0.005 for v in vector]
    r = record_and_score("proj-1", "session-b", nudged)
    assert 0.0 < r.duplicate_score <= 100.0


def test_same_session_id_never_self_matches():
    vector = _human_like_vector(2.0)
    record_and_score("proj-1", "session-a", vector)
    # Same session re-scored (e.g. repeated predict calls) must not compare
    # against its own earlier vector.
    r = record_and_score("proj-1", "session-a", vector)
    assert r.compared_against == 0
    assert r.duplicate_score == 0.0


def test_different_projects_isolated():
    vector = _human_like_vector(3.0)
    record_and_score("proj-1", "session-a", vector)
    r = record_and_score("proj-2", "session-b", list(vector))
    assert r.compared_against == 0
    assert r.duplicate_score == 0.0


def test_disabled_returns_zero(monkeypatch):
    monkeypatch.setattr(replay_detection, "REPLAY_DETECTION_DISABLED", True)
    vector = _human_like_vector(4.0)
    record_and_score("proj-1", "session-a", vector)
    r = record_and_score("proj-1", "session-b", list(vector))
    assert r.duplicate_score == 0.0


def test_missing_project_id_returns_zero():
    r = record_and_score(None, "session-a", _human_like_vector(0.0))
    assert r.duplicate_score == 0.0


def test_window_expiry_forgets_old_sessions(monkeypatch):
    ticks = iter([1000.0, 1000.0 + replay_detection._WINDOW_SECONDS + 10])
    monkeypatch.setattr(replay_detection.time, "time", lambda: next(ticks))
    vector = _human_like_vector(5.0)
    record_and_score("proj-1", "session-a", vector)
    r = record_and_score("proj-1", "session-b", list(vector))
    assert r.compared_against == 0
    assert r.duplicate_score == 0.0


def test_max_per_project_bounds_memory():
    for i in range(replay_detection._MAX_PER_PROJECT + 50):
        record_and_score("proj-1", f"session-{i}", _human_like_vector(float(i)))
    assert len(replay_detection._project_vectors["proj-1"]) == replay_detection._MAX_PER_PROJECT
