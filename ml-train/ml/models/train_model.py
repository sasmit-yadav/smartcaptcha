"""Train the v4 bot-detection models.

Single pipeline (the previous version of this file contained two concatenated
implementations; the older, broken one ran on __main__ — see
docs/MODEL_IMPROVEMENT_STRATEGY.md Finding 1).

What this produces (artifacts/v4/):
- A **calibrated** supervised classifier (RandomForest and XGBoost are both
  trained and compared; the better one is recorded in the comparison file).
  Calibration is sigmoid/Platt via CalibratedClassifierCV — the right choice
  at this data volume (isotonic needs ~1000+ samples and overfits below that).
- An **IsolationForest** anomaly detector trained on human sessions only —
  the orthogonal second detector on the behaviour axis (strategy §B.7).
- A StandardScaler fit on the full training set.
- Metadata containing the **decision_threshold picked from calibrated
  out-of-fold probabilities** — serving must consume this instead of a
  hard-coded 0.50 (Finding 2).

Evaluation methodology (strategy §1.1/§B.6 — the "your headline metric is
probably lying to you" fixes):
- Out-of-fold predictions via StratifiedGroupKFold where bot sessions are
  grouped by (heuristic) bot family, so no family straddles train/eval.
- **Out-of-time split** (`out_of_time_eval`): trained on the chronologically
  older half of sessions, tested on the newer half, by `created_at` — catches
  a model that just memorised one collection window, which grouped CV alone
  cannot detect. Its threshold is selected only from older-half grouped OOF
  predictions, never future test labels. Skips with a stated reason (not a
  fabricated number) when a time-half is single-class.
- ROC-AUC is reported alongside **PR-AUC (average precision)** and
  **FPR at a fixed 99%-bot-recall operating point** (`fpr_at_recall`) — the
  number that matters for a silent blocker, per strategy §1.1's critique
  that ROC-AUC alone is insensitive to class imbalance and operating point.
- **Bootstrap confidence intervals** (`bootstrap_metric_ci`, class-stratified
  whole-group 1000 resamples) on ROC-AUC and PR-AUC — with ~75 humans every
  point estimate needs an interval, not just a single number.
- Metrics also reported at fixed human FPR (zero false positives on the OOF
  set), not at whatever operating point maximises F1.
- A "stealth" re-evaluation with webdriver_flag zeroed for all bots, to
  measure how much recall survives when the single easiest tell is hidden.
- **No hyperparameter search.** On ~100 rows a RandomizedSearchCV fits noise;
  fixed conservative hyperparameters are more honest and reproducible.

All metric printing carries the caveat that with ~40 human sessions, one
mislabeled human swings FPR by ~2.5 points — treat every number as coarse.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import IsolationForest, RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from features.feature_columns import FEATURE_COLUMNS

ARTIFACT_VERSION = "v5"
FEATURE_VERSION = "v5"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    """Load labeled desktop session features from PostgreSQL."""
    from core.database import get_connection, init_db, release_connection

    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        selected_columns = ["session_id", *FEATURE_COLUMNS, "device_type", "label", "created_at"]
        cursor.execute(
            f"""
            SELECT {", ".join(selected_columns)}
            FROM session_features
            WHERE label IN ('bot', 'human')
              AND device_type = 'desktop'
              AND event_count > 0
            """
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        df = pd.DataFrame(rows, columns=columns)
    finally:
        release_connection(conn)

    print(f"Loaded {len(df)} labeled desktop sessions")
    if not df.empty:
        print(f"Label distribution:\n{df['label'].value_counts()}")
    return df


def preprocess_data(df):
    """Fill missing numerics, encode labels, coerce types."""
    if df.empty or df["label"].nunique() < 2:
        raise ValueError("Need at least one human and one bot session to train.")
    df = df.copy()
    df[FEATURE_COLUMNS] = (
        df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    )
    df["label_encoded"] = df["label"].map({"human": 0, "bot": 1})
    if df["label_encoded"].isnull().any():
        raise ValueError(f"Unknown labels found: {df['label'].unique()}")
    n_humans = int((df["label_encoded"] == 0).sum())
    if n_humans < 100:
        print(
            f"CAVEAT: only {n_humans} human sessions — FPR resolution is "
            f"~{100.0 / max(n_humans, 1):.1f} percentage points per sample. "
            "Treat all metrics as coarse estimates."
        )
    return df


def assign_groups(df):
    """Group labels for grouped CV.

    Bots: a heuristic behavioural family (duration x velocity bucket) — a
    proxy for the real bot-family label, which sessions don't carry yet.
    Ensures a whole family is held out together, so eval measures
    generalisation to unseen bot styles rather than memorisation.

    Humans: spread round-robin into pseudo-groups so every fold keeps some
    humans (humans have no family structure to leak).
    """
    groups = pd.Series(index=df.index, dtype=object)

    bot_mask = df["label_encoded"] == 1
    duration_bucket = pd.cut(
        df.loc[bot_mask, "session_duration"],
        bins=[-np.inf, 1, 10, np.inf],
        labels=["instant", "short", "long"],
    ).astype(str)
    velocity_bucket = pd.cut(
        df.loc[bot_mask, "avg_mouse_vel"],
        bins=[-np.inf, 100, 500, np.inf],
        labels=["slow", "medium", "fast"],
    ).astype(str)
    groups.loc[bot_mask] = "bot_" + duration_bucket + "_" + velocity_bucket

    human_idx = df.index[~bot_mask]
    for i, idx in enumerate(human_idx):
        groups.loc[idx] = f"human_{i % 8}"

    n_families = groups[bot_mask].nunique()
    print(f"Bot families (heuristic): {n_families} -> "
          f"{sorted(groups[bot_mask].unique())}")
    return groups


# ---------------------------------------------------------------------------
# Models — fixed conservative hyperparameters (deliberately no search)
# ---------------------------------------------------------------------------

def make_base_models():
    """The candidate supervised models, all trained + evaluated identically and
    compared on out-of-fold stealth recall.

    Includes exactly ONE ensemble: a soft-vote of RF + XGB. This is the *only*
    multi-model ensembling the strategy doc §B.7 sanctions at this data volume —
    "soft-vote calibrated RF + XGB (no trainable meta-layer)". voting='soft'
    averages the two models' probabilities; there is no meta-learner to overfit
    ~40 humans, and the training loop wraps every candidate in
    CalibratedClassifierCV so the served ensemble emits calibrated probabilities
    (honouring "ensemble after calibration"). Deliberately NOT done: stacking
    more correlated classifiers (LightGBM, logistic, a trained meta-layer) on the
    same 52 features — §B.7 shows that adds ~zero variance reduction and an
    overfit meta-learner on this few humans ("two models on the same features
    ≈ one model"). The substantive ensemble is the ORTHOGONAL fusion in the
    RiskEngine (behaviour + anomaly + network + velocity), not model count.
    """
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=2,
        min_samples_split=4,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=2,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    ensemble = VotingClassifier(
        estimators=[("rf", clone(rf)), ("xgb", clone(xgb_model))],
        voting="soft",
        n_jobs=-1,
    )
    return {
        "random_forest": rf,
        "xgboost": xgb_model,
        "ensemble_rf_xgb": ensemble,
    }


def _calibration_cv(y):
    """Inner CV for CalibratedClassifierCV, bounded by the minority class."""
    n_splits = int(min(3, pd.Series(y).value_counts().min()))
    return StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=42)


def fit_calibrated(base_model, X, y):
    calibrated = CalibratedClassifierCV(
        estimator=clone(base_model), method="sigmoid", cv=_calibration_cv(y)
    )
    calibrated.fit(X, y)
    return calibrated


# ---------------------------------------------------------------------------
# Out-of-fold evaluation
# ---------------------------------------------------------------------------

def out_of_fold_probabilities(base_model, df, groups, n_splits):
    """Calibrated + raw OOF probabilities via StratifiedGroupKFold.

    Scaling and calibration are fit inside each fold (no leakage).
    Returns (oof_calibrated, oof_raw) aligned to df.index; entries left as
    NaN if a fold could not be scored (should not happen in practice).
    """
    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = df["label_encoded"].to_numpy()
    oof_cal = np.full(len(df), np.nan)
    oof_raw = np.full(len(df), np.nan)

    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
        y_train = y[train_idx]
        if len(np.unique(y_train)) < 2:
            print(f"  fold {fold}: single-class training split, skipped")
            continue
        scaler = StandardScaler().fit(X[train_idx])
        X_train = scaler.transform(X[train_idx])
        X_test = scaler.transform(X[test_idx])

        raw_model = clone(base_model).fit(X_train, y_train)
        oof_raw[test_idx] = raw_model.predict_proba(X_test)[:, 1]

        cal_model = fit_calibrated(base_model, X_train, y_train)
        oof_cal[test_idx] = cal_model.predict_proba(X_test)[:, 1]

        held_out_families = sorted(set(groups.iloc[test_idx]) - {f"human_{i}" for i in range(8)})
        print(f"  fold {fold}: {len(test_idx)} samples, held-out bot families: {held_out_families}")

    return oof_cal, oof_raw


def _fmt_ci(ci):
    if not ci:
        return "n/a"
    return f"{ci['ci_low']:.3f}-{ci['ci_high']:.3f}"


def pick_threshold(y, proba):
    """Max-margin threshold with zero human false positives on the OOF set.

    Place the cut halfway between the highest-scoring human and the lowest
    bot above that point. Falls back to max_human + 0.05 when no bot scores
    above every human. Clamped to [0.15, 0.60] as a sanity guard.
    """
    human_scores = proba[y == 0]
    bot_scores = proba[y == 1]
    max_human = float(np.max(human_scores))
    bots_above = bot_scores[bot_scores > max_human]
    if len(bots_above) > 0:
        threshold = (max_human + float(np.min(bots_above))) / 2
    else:
        threshold = max_human + 0.05
    threshold = float(np.clip(threshold, 0.15, 0.60))
    return threshold, max_human


def evaluate_at_threshold(y, proba, threshold):
    pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {
        "threshold": float(threshold),
        "bot_recall": float(recall),
        "human_fpr": float(fpr),
        "precision": float(precision),
        "confusion_matrix": cm.tolist(),
        "n_humans": int(tn + fp),
        "n_bots": int(tp + fn),
    }


def per_family_recall(df, groups, proba, threshold):
    """Recall broken out per held-out bot family."""
    out = {}
    bot_mask = df["label_encoded"] == 1
    for family in sorted(groups[bot_mask].unique()):
        idx = groups[groups == family].index
        scores = proba[df.index.get_indexer(idx)]
        scores = scores[~np.isnan(scores)]
        if len(scores) == 0:
            continue
        out[family] = {
            "n": int(len(scores)),
            "recall": float(np.mean(scores >= threshold)),
            "median_p": float(np.median(scores)),
        }
    return out


def fpr_at_recall(y, proba, target_recall=0.99):
    """Human FPR at a fixed high bot-recall operating point (strategy §1.1).

    ROC-AUC is insensitive to the class imbalance and operating point that
    actually matter for a silent blocker; "at 99% bot recall, what fraction
    of humans do we wrongly block?" is the number a product decision needs.
    Walks the ROC curve (tpr non-decreasing as threshold falls) and reports
    the first point reaching target_recall. At this data volume the exact
    target may be unreachable — in that case we report the best achievable
    recall's FPR rather than fabricating a threshold that doesn't exist.
    """
    fpr, tpr, thresholds = roc_curve(y, proba)
    idx = int(np.searchsorted(tpr, target_recall, side="left"))
    idx = min(idx, len(tpr) - 1)
    thr = thresholds[idx]
    return {
        "target_recall": float(target_recall),
        "achieved_recall": float(tpr[idx]),
        "fpr": float(fpr[idx]),
        "threshold": float(thr) if np.isfinite(thr) else None,
        "note": None if tpr[idx] >= target_recall else
                f"target recall unreachable at this sample size; reporting best achievable ({tpr[idx]:.2f})",
    }


def bootstrap_metric_ci(y, proba, metric_fn, groups=None,
                        n_boot=1000, alpha=0.05, seed=42):
    """Class-stratified grouped bootstrap CI for metric_fn(y, proba) -> float.

    Strategy §1.1, "No confidence intervals": with ~75 humans every metric
    has a wide error bar that a point estimate hides. Resampling whole CV
    groups preserves the within-family correlation that grouped CV exists to
    protect against; resampling individual OOF rows would produce falsely
    narrow intervals. Class stratification keeps every draw two-class.
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    proba = np.asarray(proba)
    groups = np.arange(len(y)) if groups is None else np.asarray(groups)
    if len(groups) != len(y):
        raise ValueError("groups must align with y/proba")

    class_groups = {}
    for label in (0, 1):
        label_groups = np.unique(groups[y == label])
        if len(label_groups) == 0:
            return None
        class_groups[label] = label_groups

    def sample_class(label):
        available = class_groups[label]
        chosen = rng.choice(available, size=len(available), replace=True)
        return np.concatenate([np.flatnonzero(groups == group) for group in chosen])

    if len(class_groups[0]) == 0 or len(class_groups[1]) == 0:
        return None
    draws = []
    for _ in range(n_boot):
        h = sample_class(0)
        b = sample_class(1)
        idx = np.concatenate([h, b])
        yy, pp = y[idx], proba[idx]
        if len(np.unique(yy)) < 2:
            continue
        try:
            draws.append(metric_fn(yy, pp))
        except ValueError:
            continue
    if not draws:
        return None
    draws = np.array(draws)
    return {
        "point": float(metric_fn(y, proba)),
        "ci_low": float(np.percentile(draws, 100 * alpha / 2)),
        "ci_high": float(np.percentile(draws, 100 * (1 - alpha / 2))),
        "n_boot": int(len(draws)),
    }


def out_of_time_eval(base_model, df):
    """Train on the older half of sessions, test on the newer half.

    Strategy §1.1: grouped CV alone still lets sessions from the same
    collection period land on both sides of the split (e.g. every bot
    scraped in one afternoon shares infra/timing quirks). An out-of-time
    split additionally checks the model isn't just memorising a single
    collection window. Requires `created_at` and at least one bot + one
    human on each side of the split; otherwise reports why it was skipped
    rather than fabricating a number from a single-class half.
    """
    if "created_at" not in df.columns or df["created_at"].isna().all():
        return {"skipped": True, "reason": "created_at not available"}

    df_sorted = df.sort_values("created_at").reset_index(drop=True)
    split = len(df_sorted) // 2
    train_df, test_df = df_sorted.iloc[:split], df_sorted.iloc[split:]
    if train_df["label_encoded"].nunique() < 2 or test_df["label_encoded"].nunique() < 2:
        return {"skipped": True, "reason": "one time-half is single-class at this data volume"}

    X_train = train_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    X_test = test_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train_df["label_encoded"].to_numpy()
    y_test = test_df["label_encoded"].to_numpy()

    # Select the operating threshold using only the older training half.
    # Passing the full-dataset OOF threshold here would leak future labels
    # into the reported out-of-time recall/FPR.
    train_groups = assign_groups(train_df)
    n_bot_families = train_groups[train_df["label_encoded"] == 1].nunique()
    n_splits = int(np.clip(
        min(n_bot_families, train_df["label_encoded"].value_counts().min()),
        2,
        4,
    ))
    train_oof, _ = out_of_fold_probabilities(
        base_model,
        train_df,
        train_groups,
        n_splits,
    )
    threshold_valid = ~np.isnan(train_oof)
    if (
        not threshold_valid.any()
        or len(np.unique(y_train[threshold_valid])) < 2
    ):
        return {
            "skipped": True,
            "reason": "older half produced no two-class OOF threshold scores",
        }
    threshold, _ = pick_threshold(y_train[threshold_valid], train_oof[threshold_valid])

    scaler = StandardScaler().fit(X_train)
    model = fit_calibrated(base_model, scaler.transform(X_train), y_train)
    proba = model.predict_proba(scaler.transform(X_test))[:, 1]

    result = evaluate_at_threshold(y_test, proba, threshold)
    result["skipped"] = False
    result["oof_roc_auc"] = (
        float(roc_auc_score(y_test, proba)) if len(np.unique(y_test)) > 1 else None
    )
    result["train_period"] = [str(train_df["created_at"].min()), str(train_df["created_at"].max())]
    result["test_period"] = [str(test_df["created_at"].min()), str(test_df["created_at"].max())]
    result["note"] = "trained on the chronologically older half, tested on the newer half"
    result["threshold_source"] = "older-half grouped OOF only"
    return result


def stealth_evaluation(base_model, df, groups, n_splits, threshold):
    """Re-run OOF eval with webdriver_flag zeroed on bot rows at TEST time.

    Simulates every bot hiding navigator.webdriver (what stealth kits do).
    Training folds keep the true flag; only the evaluation-side features are
    altered. Measures how much recall rests on the single easiest tell.
    """
    if "webdriver_flag" not in FEATURE_COLUMNS:
        return None
    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y = df["label_encoded"].to_numpy()
    wd_col = FEATURE_COLUMNS.index("webdriver_flag")

    oof = np.full(len(df), np.nan)
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for train_idx, test_idx in sgkf.split(X, y, groups):
        if len(np.unique(y[train_idx])) < 2:
            continue
        scaler = StandardScaler().fit(X[train_idx])
        cal_model = fit_calibrated(base_model, scaler.transform(X[train_idx]), y[train_idx])
        X_test = X[test_idx].copy()
        X_test[y[test_idx] == 1, wd_col] = 0.0
        oof[test_idx] = cal_model.predict_proba(scaler.transform(X_test))[:, 1]

    valid = ~np.isnan(oof)
    result = evaluate_at_threshold(y[valid], oof[valid], threshold)
    result["note"] = "bots' webdriver_flag zeroed at eval time (stealth simulation)"
    return result


# ---------------------------------------------------------------------------
# Anomaly detector (human-only)
# ---------------------------------------------------------------------------

def train_anomaly_detector(df, scaler):
    """IsolationForest on human sessions only (strategy §B.1/§B.7).

    Calibration anchors for serving (piecewise-linear score -> 0-100 points):
    - score_zero: median human score  -> 0 points
    - score_block: min human score minus a margin -> 50 points (the block
      boundary). No training human can reach >= 50 by construction.
    Scores below score_block extrapolate linearly toward 100.
    """
    human_X = df.loc[df["label_encoded"] == 0, FEATURE_COLUMNS].to_numpy(dtype=float)
    bot_X = df.loc[df["label_encoded"] == 1, FEATURE_COLUMNS].to_numpy(dtype=float)

    forest = IsolationForest(
        n_estimators=300, contamination="auto", random_state=42, n_jobs=-1
    )
    forest.fit(scaler.transform(human_X))

    human_scores = forest.decision_function(scaler.transform(human_X))
    bot_scores = forest.decision_function(scaler.transform(bot_X)) if len(bot_X) else np.array([])

    score_zero = float(np.median(human_scores))
    min_human = float(np.min(human_scores))
    margin = max(0.25 * (score_zero - min_human), 1e-3)
    score_block = min_human - margin

    flagged_bots = float(np.mean(bot_scores < score_block)) if len(bot_scores) else 0.0
    print(f"IsolationForest: median human score {score_zero:.4f}, "
          f"block anchor {score_block:.4f}, "
          f"bots below block anchor: {flagged_bots:.1%}")

    anomaly_meta = {
        "score_zero": score_zero,
        "score_block": score_block,
        "human_score_min": min_human,
        "human_score_p05": float(np.percentile(human_scores, 5)),
        "bot_fraction_below_block": flagged_bots,
        "n_humans_trained_on": int(len(human_X)),
    }
    return forest, anomaly_meta


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def save_artifacts(artifacts_dir, timestamp, model_name, calibrated_model, scaler,
                   metrics, feature_importance, threshold_info, anomaly_meta):
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_dir / f"{model_name}_{timestamp}.pkl"
    scaler_path = artifacts_dir / f"scaler_{timestamp}.pkl"
    metrics_path = artifacts_dir / f"{model_name}_metrics_{timestamp}.json"
    importance_path = artifacts_dir / f"{model_name}_feature_importance_{timestamp}.csv"
    metadata_path = artifacts_dir / f"{model_name}_metadata_{timestamp}.json"

    joblib.dump(calibrated_model, model_path)
    joblib.dump(scaler, scaler_path)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    if feature_importance is not None:
        feature_importance.to_csv(importance_path, index=False)

    metadata = {
        "model_name": model_name,
        "created_at": datetime.now().isoformat(),
        "feature_version": FEATURE_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "calibration": "sigmoid (CalibratedClassifierCV)",
        "feature_columns": FEATURE_COLUMNS,
        "decision_threshold": threshold_info["threshold"],
        "threshold_metrics": threshold_info,
        "anomaly": anomaly_meta,
        "training_methodology": "StratifiedGroupKFold OOF by heuristic bot family + "
                                "out-of-time split with older-half OOF threshold; "
                                "threshold at zero human FP on calibrated OOF probs; "
                                "PR-AUC and FPR@99%-recall reported alongside ROC-AUC "
                                "with grouped-bootstrap CIs; "
                                "no hyperparameter search (98-row regime)",
        "optimization_target": "zero_human_fp_max_margin",
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved {model_name} artifacts to {artifacts_dir}")
    return {
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "metrics_path": str(metrics_path),
        "importance_path": str(importance_path),
        "metadata_path": str(metadata_path),
    }


def get_feature_importance(calibrated_model, feature_names):
    """Mean feature importance across the calibrated ensemble's base estimators."""
    importances = []
    for cc in getattr(calibrated_model, "calibrated_classifiers_", []):
        est = cc.estimator
        if hasattr(est, "feature_importances_"):
            importances.append(est.feature_importances_)
    if not importances:
        return None
    return pd.DataFrame(
        {"feature": feature_names, "importance": np.mean(importances, axis=0)}
    ).sort_values("importance", ascending=False)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_training(df, artifacts_dir=None, quick=False):
    """Full training pass on a prepared DataFrame. Returns the comparison dict.

    `quick=True` trims tree counts for CI smoke tests; identical code path.
    """
    df = preprocess_data(df)
    df = df.reset_index(drop=True)
    groups = assign_groups(df)
    y = df["label_encoded"].to_numpy()

    n_bot_families = groups[df["label_encoded"] == 1].nunique()
    n_splits = int(np.clip(min(n_bot_families, df["label_encoded"].value_counts().min()), 2, 4))
    print(f"Grouped CV: {n_splits} splits over {n_bot_families} bot families")

    base_models = make_base_models()
    if quick:
        for m in base_models.values():
            if isinstance(m, VotingClassifier):
                m.set_params(rf__n_estimators=25, xgb__n_estimators=25)
            else:
                m.set_params(n_estimators=25)

    if artifacts_dir is None:
        artifacts_dir = ROOT / "ml" / "models" / "artifacts" / ARTIFACT_VERSION
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Final scaler: fit on all data (folds re-fit their own — no leakage there).
    scaler = StandardScaler().fit(df[FEATURE_COLUMNS].to_numpy(dtype=float))
    X_all = scaler.transform(df[FEATURE_COLUMNS].to_numpy(dtype=float))

    anomaly_forest, anomaly_meta = train_anomaly_detector(df, scaler)
    anomaly_path = artifacts_dir / f"isolation_forest_{timestamp}.pkl"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(anomaly_forest, anomaly_path)
    anomaly_meta["model_path"] = str(anomaly_path)

    comparison = {"timestamp": datetime.now().isoformat(),
                  "feature_version": FEATURE_VERSION,
                  "artifact_version": ARTIFACT_VERSION,
                  "n_sessions": int(len(df)),
                  "n_humans": int((y == 0).sum()),
                  "n_bots": int((y == 1).sum()),
                  "models": {}}

    for model_name, base_model in base_models.items():
        print(f"\n=== {model_name} ===")
        oof_cal, oof_raw = out_of_fold_probabilities(base_model, df, groups, n_splits)
        valid = ~np.isnan(oof_cal)
        y_v, p_cal, p_raw = y[valid], oof_cal[valid], oof_raw[valid]
        groups_v = groups.iloc[np.flatnonzero(valid)].to_numpy()

        threshold, max_human_p = pick_threshold(y_v, p_cal)
        thr_metrics = evaluate_at_threshold(y_v, p_cal, threshold)
        thr_metrics["max_human_oof_probability"] = max_human_p

        metrics = {
            "oof_roc_auc": float(roc_auc_score(y_v, p_cal)),
            "oof_roc_auc_ci": bootstrap_metric_ci(
                y_v, p_cal, roc_auc_score, groups=groups_v
            ),
            "oof_pr_auc": float(average_precision_score(y_v, p_cal)),
            "oof_pr_auc_ci": bootstrap_metric_ci(
                y_v, p_cal, average_precision_score, groups=groups_v
            ),
            "oof_brier_calibrated": float(brier_score_loss(y_v, p_cal)),
            "oof_brier_uncalibrated": float(brier_score_loss(y_v, p_raw))
            if not np.isnan(p_raw).any() else None,
            "fpr_at_99pct_recall": fpr_at_recall(y_v, p_cal, target_recall=0.99),
            "at_threshold": thr_metrics,
            "per_family_recall": per_family_recall(df, groups, oof_cal, threshold),
            "stealth_eval": stealth_evaluation(base_model, df, groups, n_splits, threshold),
            "out_of_time_eval": out_of_time_eval(base_model, df),
            "caveat": f"OOF over {int(valid.sum())} sessions "
                      f"({int((y_v == 0).sum())} humans) — coarse estimates; "
                      f"treat all CIs as wide at this sample size",
        }

        print(f"OOF ROC-AUC: {metrics['oof_roc_auc']:.4f} "
              f"(95% CI {_fmt_ci(metrics['oof_roc_auc_ci'])})")
        print(f"OOF PR-AUC: {metrics['oof_pr_auc']:.4f} "
              f"(95% CI {_fmt_ci(metrics['oof_pr_auc_ci'])})")
        print(f"Brier (calibrated): {metrics['oof_brier_calibrated']:.4f}")
        fpr99 = metrics["fpr_at_99pct_recall"]
        print(f"FPR @ {fpr99['achieved_recall']:.0%} bot recall "
              f"(target 99%): {fpr99['fpr']:.3f}"
              + (f" — {fpr99['note']}" if fpr99["note"] else ""))
        print(f"Threshold {threshold:.3f}: recall {thr_metrics['bot_recall']:.3f} "
              f"@ human FPR {thr_metrics['human_fpr']:.3f}")
        if metrics["stealth_eval"]:
            print(f"Stealth recall (webdriver hidden): "
                  f"{metrics['stealth_eval']['bot_recall']:.3f}")
        oot = metrics["out_of_time_eval"]
        if oot.get("skipped"):
            print(f"Out-of-time eval skipped: {oot['reason']}")
        else:
            print(f"Out-of-time recall: {oot['bot_recall']:.3f} "
                  f"@ human FPR {oot['human_fpr']:.3f} "
                  f"(train {oot['train_period'][0][:10]}..{oot['train_period'][1][:10]}, "
                  f"test {oot['test_period'][0][:10]}..{oot['test_period'][1][:10]})")

        final_model = fit_calibrated(base_model, X_all, y)
        importance = get_feature_importance(final_model, FEATURE_COLUMNS)
        if importance is not None:
            print(f"Top features:\n{importance.head(10).to_string(index=False)}")

        artifacts = save_artifacts(
            artifacts_dir, timestamp, model_name, final_model, scaler,
            metrics, importance, thr_metrics, anomaly_meta,
        )
        comparison["models"][model_name] = {"metrics": metrics, "artifacts": artifacts}

    # Model selection: stealth recall first (the demonstrated gap), then AUC.
    def _score(name):
        m = comparison["models"][name]["metrics"]
        stealth = m["stealth_eval"]["bot_recall"] if m["stealth_eval"] else 0.0
        return (m["at_threshold"]["bot_recall"], stealth, m["oof_roc_auc"])

    best = max(comparison["models"], key=_score)
    comparison["best_model"] = best
    # Keys the serving loader (sdk-backend BotDetector) reads directly:
    comparison[best] = comparison["models"][best]

    comparison_path = artifacts_dir / f"model_comparison_{timestamp}.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\nBest model: {best}")
    print(f"Saved comparison to {comparison_path}")
    return comparison


def main():
    parser = argparse.ArgumentParser(description="Train v4 bot-detection models")
    parser.add_argument("--quick", action="store_true",
                        help="Small tree counts (CI smoke test)")
    args = parser.parse_args()

    print("=" * 60)
    print("v4 model training — calibrated, group-CV, fixed-FPR thresholds")
    print("=" * 60)
    df = load_data()
    run_training(df, quick=args.quick)
    print("\nTraining complete.")


if __name__ == "__main__":
    main()
