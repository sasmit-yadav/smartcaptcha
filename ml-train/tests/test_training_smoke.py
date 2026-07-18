"""Training-pipeline smoke test (strategy step 0.5 / Finding 1 regression guard).

Runs the real run_training() code path on a small synthetic fixture — no
database, no network. If the pipeline rots again (duplicate defs, broken
imports, missing sklearn symbols), this fails in CI instead of being
discovered months later when someone tries to retrain.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ML_TRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_TRAIN))
sys.path.insert(0, str(ML_TRAIN / "ml"))

from ml.models.train_model import run_training  # noqa: E402
from features.feature_columns import FEATURE_COLUMNS  # noqa: E402


def synthetic_sessions(n_humans=30, n_bots=45, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_humans):
        row = {c: abs(rng.normal(50, 20)) for c in FEATURE_COLUMNS}
        row.update(
            session_duration=rng.uniform(5, 60),
            avg_mouse_vel=rng.uniform(50, 400),
            webdriver_flag=0,
            event_count=int(rng.integers(50, 500)),
            label="human",
        )
        rows.append(row)
    for _ in range(n_bots):
        row = {c: abs(rng.normal(150, 60)) for c in FEATURE_COLUMNS}
        row.update(
            session_duration=float(rng.choice([0.5, 3.0, 30.0])),
            avg_mouse_vel=float(rng.choice([50.0, 300.0, 900.0])),
            webdriver_flag=int(rng.random() < 0.7),
            event_count=int(rng.integers(5, 100)),
            label="bot",
        )
        rows.append(row)
    df = pd.DataFrame(rows)
    df["session_id"] = [f"s{i}" for i in range(len(df))]
    df["device_type"] = "desktop"
    return df


def test_run_training_end_to_end(tmp_path):
    comparison = run_training(synthetic_sessions(), artifacts_dir=tmp_path, quick=True)

    assert comparison["best_model"] in ("random_forest", "xgboost")
    for model_name, entry in comparison["models"].items():
        metrics = entry["metrics"]
        assert 0.5 <= metrics["oof_roc_auc"] <= 1.0
        thr = metrics["at_threshold"]["threshold"]
        assert 0.15 <= thr <= 0.60
        assert metrics["at_threshold"]["human_fpr"] == 0.0, (
            "threshold must produce zero human FP on the OOF set"
        )
        assert metrics["stealth_eval"] is not None
        for key in ("model_path", "scaler_path", "metadata_path"):
            assert Path(entry["artifacts"][key]).exists()

    # Anomaly detector artifact + calibration anchors present
    forests = list(tmp_path.glob("isolation_forest_*.pkl"))
    assert len(forests) == 1
    import json
    meta_path = Path(comparison["models"][comparison["best_model"]]["artifacts"]["metadata_path"])
    metadata = json.loads(meta_path.read_text())
    assert metadata["decision_threshold"] == metadata["threshold_metrics"]["threshold"]
    anomaly = metadata["anomaly"]
    assert anomaly["score_block"] < anomaly["score_zero"], (
        "block anchor must be more anomalous (lower) than the zero anchor"
    )


def test_training_rejects_single_class():
    df = synthetic_sessions(n_humans=10, n_bots=0)
    df = df[df["label"] == "human"]
    with pytest.raises(ValueError):
        run_training(df, quick=True)
