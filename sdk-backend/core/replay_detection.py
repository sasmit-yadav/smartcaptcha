"""
Replay-trace detection (strategy doc Part D.2).

Behavioral features can't distinguish a genuine live human from a recording
of a real human replayed through automation — the replayed events produce
the exact same derived features, because the features are a deterministic
function of the raw input, and the input really was human once. No amount of
neuromotor feature engineering closes that gap (see MODEL_IMPROVEMENT_
STRATEGY.md Part D.2): it's a structural ceiling for any behavior-only model.

What CAN be caught without a challenge tier: a genuine human never reproduces
a byte-identical (or near-identical) behavioral fingerprint across two
different sessions — natural motor variability means every real session's
feature vector differs at least a little. A replayed recording, by
definition, reproduces the same fingerprint every time it's replayed. So
instead of asking "does this session look human," this asks "have I already
seen a session whose full behavioral feature vector is suspiciously close to
this one" — a duplicate/reuse signal, not a shape-of-motion signal.

Implementation mirrors core/velocity.py deliberately: an in-process,
per-project sliding window (no Redis — single Render instance; horizontal
scaling would need a shared store, same caveat velocity.py documents).

Distance is computed in the model's own SCALED feature space (the same
StandardScaler transform used for inference), passed in by the caller
(models/inference.py) — this module has no model/scaler dependency of its
own and just compares whatever vectors it's given.

Thresholds are provisional (SOFT/HARD env-configurable) since no confirmed
real replay-attack sample exists yet to calibrate against — same honest
caveat this project applies to any untuned signal. Revisit once real
adversarial replay data exists.

REPLAY_DETECTION_DISABLED=1 turns it off (returns 0 always).
"""
from __future__ import annotations

import math
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Sequence

REPLAY_DETECTION_DISABLED = os.getenv("REPLAY_DETECTION_DISABLED", "0") == "1"

# Rolling window over which prior sessions are remembered per project.
_WINDOW_SECONDS = int(os.getenv("REPLAY_WINDOW_SECONDS", str(6 * 3600)))  # 6h
# Bound memory regardless of traffic volume.
_MAX_PER_PROJECT = int(os.getenv("REPLAY_MAX_PER_PROJECT", "2000"))

# Euclidean distance in scaled (StandardScaler) feature space. Below SOFT,
# no risk; at/below HARD, saturates to 100. Provisional — see module docstring.
_DIST_SOFT = float(os.getenv("REPLAY_DIST_SOFT", "1.5"))
_DIST_HARD = float(os.getenv("REPLAY_DIST_HARD", "0.4"))

_lock = threading.Lock()
# project_id -> deque[(timestamp, session_id, vector)]
_project_vectors: dict = {}


@dataclass
class ReplayResult:
    duplicate_score: float                 # 0-100
    nearest_distance: Optional[float]       # Euclidean distance to closest prior session, None if no comparison made
    nearest_session_id: Optional[str]
    compared_against: int                   # how many prior sessions were checked
    reasons: list = field(default_factory=list)


def _euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _ramp_down(distance: float, soft: float, hard: float, ceiling: float = 100.0) -> float:
    """Inverse ramp: 0 risk at/above `soft` distance, `ceiling` at/below `hard`."""
    if distance >= soft:
        return 0.0
    if distance <= hard:
        return ceiling
    return ceiling * (soft - distance) / (soft - hard)


def record_and_score(project_id: Optional[str], session_id: Optional[str],
                      feature_vector: Sequence[float]) -> ReplayResult:
    """Compare `feature_vector` (already scaled, same space the model scores
    on) against recent sessions from the same project, then record it.

    Excludes comparisons against entries with the same session_id — a
    session's own vector recomputed across repeated predict calls as more
    events accumulate is expected to shift slightly and is not a replay
    signal against itself.
    """
    empty = ReplayResult(0.0, None, None, 0)
    if REPLAY_DETECTION_DISABLED or not project_id or feature_vector is None:
        return empty

    vector = list(feature_vector)
    now = time.time()
    cutoff = now - _WINDOW_SECONDS

    with _lock:
        dq = _project_vectors.setdefault(project_id, deque())
        while dq and dq[0][0] < cutoff:
            dq.popleft()

        nearest_distance = None
        nearest_session_id = None
        compared = 0
        for ts, other_session_id, other_vector in dq:
            if session_id is not None and other_session_id == session_id:
                continue
            compared += 1
            dist = _euclidean(vector, other_vector)
            if nearest_distance is None or dist < nearest_distance:
                nearest_distance = dist
                nearest_session_id = other_session_id

        dq.append((now, session_id, vector))
        while len(dq) > _MAX_PER_PROJECT:
            dq.popleft()

    reasons: list = []
    duplicate_score = 0.0
    if nearest_distance is not None:
        duplicate_score = _ramp_down(nearest_distance, _DIST_SOFT, _DIST_HARD)
        if duplicate_score > 0:
            reasons.append(
                f"behavioral feature vector distance {nearest_distance:.3f} to "
                f"prior session {nearest_session_id} (soft={_DIST_SOFT}, hard={_DIST_HARD})"
            )

    return ReplayResult(
        duplicate_score=duplicate_score,
        nearest_distance=nearest_distance,
        nearest_session_id=nearest_session_id,
        compared_against=compared,
        reasons=reasons,
    )


def reset() -> None:
    """Clear all windows — for tests."""
    with _lock:
        _project_vectors.clear()
