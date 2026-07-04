"""Train V2 supervised ML models for bot detection."""
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, init_db, release_connection
from features.feature_columns import FEATURE_COLUMNS

load_dotenv(ROOT / "backend" / ".env")


def load_data():
    """Load desktop session features from PostgreSQL."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        selected_columns = ["session_id", *FEATURE_COLUMNS, "device_type", "label"]
        cursor.execute(
            f"""
            SELECT {", ".join(selected_columns)}
            FROM session_features
            WHERE device_type = 'desktop'
            AND label IS NOT NULL
            AND event_count > 0
            """
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        df = pd.DataFrame(rows, columns=columns)
    finally:
        release_connection(conn)

    print(f"Loaded {len(df)} desktop sessions")
    if not df.empty:
        print(f"Label distribution:\n{df['label'].value_counts()}")
    if len(df) < 200:
        print("Warning: dataset is small; treat perfect scores as suspicious.")
    if df.empty or df["label"].nunique() < 2:
        raise ValueError("Need at least one human and one bot session to train.")
    return df


def preprocess_data(df):
    """Fill missing numeric features and encode labels."""
    df = df.fillna(0)
    df["label_encoded"] = df["label"].map({"human": 0, "bot": 1})
    if df["label_encoded"].isnull().any():
        raise ValueError(f"Unknown labels found: {df['label'].unique()}")
    return df


def split_data(df):
    """Create train, validation, and final test splits with bot family separation."""
    X = df[FEATURE_COLUMNS]
    y = df["label_encoded"]
    
    # For bots, try to split by bot family to avoid leakage
    bot_df = df[df['label_encoded'] == 1].copy()
    human_df = df[df['label_encoded'] == 0].copy()
    
    print(f"Bot sessions: {len(bot_df)}")
    print(f"Human sessions: {len(human_df)}")
    
    # Simple heuristic: use behavioral clustering to simulate bot families
    # In production, this would use actual bot_family labels
    if len(bot_df) > 0:
        # Cluster bots by session_duration and avg_mouse_vel
        bot_df['duration_cluster'] = pd.cut(
            bot_df['session_duration'], 
            bins=[-1, 1, 10, float('inf')], 
            labels=['instant', 'short', 'long']
        )
        bot_df['velocity_cluster'] = pd.cut(
            bot_df['avg_mouse_vel'], 
            bins=[-1, 100, 500, float('inf')], 
            labels=['slow', 'medium', 'fast']
        )
        bot_df['bot_family'] = bot_df['duration_cluster'].astype(str) + '_' + bot_df['velocity_cluster'].astype(str)
        
        # Split bot families: train on some, test on others
        unique_families = bot_df['bot_family'].unique()
        if len(unique_families) >= 2:
            train_families = unique_families[:len(unique_families)//2]
            test_families = unique_families[len(unique_families)//2:]
            
            bot_train = bot_df[bot_df['bot_family'].isin(train_families)]
            bot_test = bot_df[bot_df['bot_family'].isin(test_families)]
            
            print(f"Bot families for training: {train_families}")
            print(f"Bot families for testing: {test_families}")
        else:
            # Fallback to random split if not enough families
            bot_train, bot_test = train_test_split(bot_df, test_size=0.3, random_state=42)
            print("Warning: Not enough bot families, using random split")
    else:
        bot_train = pd.DataFrame(columns=bot_df.columns)
        bot_test = pd.DataFrame(columns=bot_df.columns)
    
    # Split humans randomly (humans don't have families)
    if len(human_df) > 0:
        human_train, human_test = train_test_split(human_df, test_size=0.3, random_state=42)
    else:
        human_train = pd.DataFrame(columns=human_df.columns)
        human_test = pd.DataFrame(columns=human_df.columns)
    
    # Combine train and test sets
    train_full = pd.concat([bot_train, human_train])
    test_full = pd.concat([bot_test, human_test])
    
    # Split train into train and validation
    if len(train_full) > 0:
        X_train_full = train_full[FEATURE_COLUMNS]
        y_train_full = train_full["label_encoded"]
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_full, y_train_full, test_size=0.25, random_state=43, stratify=y_train_full
        )
    else:
        X_train, X_val, y_train, y_val = None, None, None, None
    
    X_test = test_full[FEATURE_COLUMNS]
    y_test = test_full["label_encoded"]
    
    print(f"Train set: {len(X_train) if X_train is not None else 0} samples")
    print(f"Validation set: {len(X_val) if X_val is not None else 0} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Test set composition: {y_test.value_counts().to_dict()}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def scale_features(X_train, X_val, X_test):
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_val_scaled, X_test_scaled, scaler


def cv_folds(y):
    min_class = int(y.value_counts().min())
    return max(2, min(5, min_class))


def train_random_forest(X_train, y_train):
    print("\n=== Training Random Forest ===")
    rf = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    param_dist = {
        "n_estimators": [100, 200, 300, 500],
        "max_depth": [5, 10, 15, 20, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2"],
    }
    search = RandomizedSearchCV(
        rf,
        param_distributions=param_dist,
        n_iter=40,
        cv=cv_folds(y_train),
        scoring="f1",
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    search.fit(X_train, y_train)
    print(f"Best RF params: {search.best_params_}")
    print(f"Best RF CV F1: {search.best_score_:.4f}")
    return search.best_estimator_


def train_xgboost(X_train, y_train):
    print("\n=== Training XGBoost ===")
    positives = int(sum(y_train))
    negatives = int(len(y_train) - positives)
    scale_pos_weight = negatives / positives if positives else 1
    print(f"Scale positive weight: {scale_pos_weight:.2f}")
    model = xgb.XGBClassifier(
        n_estimators=200,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        n_jobs=-1,
    )
    param_dist = {
        "n_estimators": [100, 200, 300, 500],
        "learning_rate": [0.01, 0.03, 0.05, 0.1],
        "max_depth": [3, 5, 7, 10],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 3, 5],
    }
    search = RandomizedSearchCV(
        model,
        param_distributions=param_dist,
        n_iter=40,
        cv=cv_folds(y_train),
        scoring="f1",
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    search.fit(X_train, y_train)
    print(f"Best XGBoost params: {search.best_params_}")
    print(f"Best XGBoost CV F1: {search.best_score_:.4f}")
    return search.best_estimator_


def evaluate_model(model, X_test, y_test, model_name, threshold=0.5):
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    roc_auc = roc_auc_score(y_test, probabilities)
    cm = confusion_matrix(y_test, predictions)
    print(f"\n=== {model_name} Test Results @ threshold {threshold:.2f} ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    print(classification_report(y_test, predictions, zero_division=0))
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "threshold": float(threshold),
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_test, predictions, output_dict=True, zero_division=0
        ),
    }


def cross_validate_model(model, X_train, y_train, model_name):
    print(f"\n=== {model_name} Cross-Validation ===")
    cv = StratifiedKFold(n_splits=cv_folds(y_train), shuffle=True, random_state=42)
    scores = {"precision": [], "recall": [], "f1": [], "roc_auc": []}
    for train_idx, val_idx in cv.split(X_train, y_train):
        fold_model = type(model)(**model.get_params())
        fold_model.fit(X_train[train_idx], y_train.iloc[train_idx])
        pred = fold_model.predict(X_train[val_idx])
        proba = fold_model.predict_proba(X_train[val_idx])[:, 1]
        y_val = y_train.iloc[val_idx]
        scores["precision"].append(precision_score(y_val, pred, zero_division=0))
        scores["recall"].append(recall_score(y_val, pred, zero_division=0))
        scores["f1"].append(f1_score(y_val, pred, zero_division=0))
        scores["roc_auc"].append(roc_auc_score(y_val, proba))
    for metric, values in scores.items():
        print(f"CV {metric}: {np.mean(values):.4f} +/- {np.std(values):.4f}")
    return scores


def tune_threshold(model, X_val, y_val, min_bot_recall=0.95, max_fpr=0.01):
    """Pick a validation threshold optimizing for false positive rate < 1%."""
    probabilities = model.predict_proba(X_val)[:, 1]
    candidates = np.linspace(0.05, 0.95, 91)
    best = None
    
    for threshold in candidates:
        pred = (probabilities >= threshold).astype(int)
        
        # Calculate metrics
        precision = precision_score(y_val, pred, zero_division=0)
        recall = recall_score(y_val, pred, zero_division=0)
        f1 = f1_score(y_val, pred, zero_division=0)
        
        # Calculate false positive rate
        cm = confusion_matrix(y_val, pred)
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        else:
            fpr = 0
        
        row = {
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "fpr": float(fpr),
        }
        
        # Stage 4B: Optimize for false positive rate < 1%
        # Priority: FPR < 1% > high bot recall > high F1
        if fpr <= max_fpr and recall >= min_bot_recall:
            if best is None or f1 > best["f1"]:
                best = row
        elif best is None:
            best = row
    
    if best is None:
        # Fallback: find threshold with lowest FPR
        best = min(
            (
                {
                    "threshold": float(t),
                    "precision": float(precision_score(y_val, (probabilities >= t).astype(int), zero_division=0)),
                    "recall": float(recall_score(y_val, (probabilities >= t).astype(int), zero_division=0)),
                    "f1": float(f1_score(y_val, (probabilities >= t).astype(int), zero_division=0)),
                    "fpr": 0.0,  # Will calculate below
                }
                for t in candidates
            ),
            key=lambda item: item["threshold"],  # Prefer higher threshold (more conservative)
        )
    
    print(
        f"Tuned threshold: {best['threshold']:.2f} "
        f"(precision={best['precision']:.4f}, recall={best['recall']:.4f}, f1={best['f1']:.4f}, fpr={best['fpr']:.4f})"
    )
    if best['fpr'] > max_fpr:
        print(f"Warning: Could not achieve FPR < {max_fpr}, got {best['fpr']:.4f}")
    
    return best


def get_feature_importance(model, feature_names):
    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    else:
        booster_scores = model.get_booster().get_score(importance_type="gain")
        importance = [booster_scores.get(f"f{i}", 0) for i, _ in enumerate(feature_names)]
    return pd.DataFrame({"feature": feature_names, "importance": importance}).sort_values(
        "importance", ascending=False
    )


def save_artifacts(model, scaler, metrics, feature_importance, model_name, threshold_info):
    artifacts_dir = ROOT / "ml" / "models" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_path = artifacts_dir / f"{model_name}_{timestamp}.pkl"
    scaler_path = artifacts_dir / f"scaler_{timestamp}.pkl"
    metrics_path = artifacts_dir / f"{model_name}_metrics_{timestamp}.json"
    importance_path = artifacts_dir / f"{model_name}_feature_importance_{timestamp}.csv"
    metadata_path = artifacts_dir / f"{model_name}_metadata_{timestamp}.json"

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    feature_importance.to_csv(importance_path, index=False)
    metadata = {
        "model_name": model_name,
        "created_at": datetime.now().isoformat(),
        "feature_version": "v4",
        "feature_columns": FEATURE_COLUMNS,
        "decision_threshold": threshold_info["threshold"],
        # Binary classification (no challenges)
        "binary_threshold": 0.50,      # Score < 0.50: allow, Score >= 0.50: block
        "threshold_metrics": threshold_info,
        "training_methodology": "bot_family_split",  # Stage 4A
        "optimization_target": "fpr_1_percent",  # Stage 4B
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved model to {model_path}")
    print(f"Saved scaler to {scaler_path}")
    print(f"Saved metrics to {metrics_path}")
    print(f"Saved feature importance to {importance_path}")
    print(f"Saved metadata to {metadata_path}")
    return {
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "metrics_path": str(metrics_path),
        "importance_path": str(importance_path),
        "metadata_path": str(metadata_path),
    }


def summarize_cv(scores):
    return {k: {"mean": float(np.mean(v)), "std": float(np.std(v))} for k, v in scores.items()}


def main():
    print("=" * 60)
    print("PHASE 7: Model Training (V2)")
    print("=" * 60)

    df = preprocess_data(load_data())
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(df)
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = scale_features(X_train, X_val, X_test)

    rf_model = train_random_forest(X_train_scaled, y_train)
    rf_cv_scores = cross_validate_model(rf_model, X_train_scaled, y_train, "Random Forest")
    rf_threshold = tune_threshold(rf_model, X_val_scaled, y_val)
    rf_metrics = evaluate_model(rf_model, X_test_scaled, y_test, "Random Forest", rf_threshold["threshold"])
    rf_importance = get_feature_importance(rf_model, FEATURE_COLUMNS)
    print(f"\nRandom Forest Feature Importance:\n{rf_importance.head(20)}")
    rf_artifacts = save_artifacts(
        rf_model, scaler, rf_metrics, rf_importance, "random_forest", rf_threshold
    )

    xgb_model = train_xgboost(X_train_scaled, y_train)
    xgb_cv_scores = cross_validate_model(xgb_model, X_train_scaled, y_train, "XGBoost")
    xgb_threshold = tune_threshold(xgb_model, X_val_scaled, y_val)
    xgb_metrics = evaluate_model(xgb_model, X_test_scaled, y_test, "XGBoost", xgb_threshold["threshold"])
    xgb_importance = get_feature_importance(xgb_model, FEATURE_COLUMNS)
    print(f"\nXGBoost Feature Importance:\n{xgb_importance.head(20)}")
    xgb_artifacts = save_artifacts(
        xgb_model, scaler, xgb_metrics, xgb_importance, "xgboost", xgb_threshold
    )

    rf_score = (rf_metrics["f1"], rf_metrics["roc_auc"])
    xgb_score = (xgb_metrics["f1"], xgb_metrics["roc_auc"])
    best_model_name = "random_forest" if rf_score >= xgb_score else "xgboost"
    comparison = {
        "random_forest": {
            "test_metrics": rf_metrics,
            "cv_scores": summarize_cv(rf_cv_scores),
            "threshold": rf_threshold,
            "artifacts": rf_artifacts,
        },
        "xgboost": {
            "test_metrics": xgb_metrics,
            "cv_scores": summarize_cv(xgb_cv_scores),
            "threshold": xgb_threshold,
            "artifacts": xgb_artifacts,
        },
        "best_model": best_model_name,
        "feature_version": "v2",
        "feature_columns": FEATURE_COLUMNS,
        "timestamp": datetime.now().isoformat(),
    }
    comparison_path = (
        ROOT
        / "ml"
        / "models"
        / "artifacts"
        / f"model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\nBest model: {best_model_name}")
    print(f"Saved comparison to {comparison_path}")
    print("\nTraining complete.")


if __name__ == "__main__":
    main()
