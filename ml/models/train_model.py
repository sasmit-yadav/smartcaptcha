"""
Train V1 supervised ML model for bot detection.
Implements Random Forest and XGBoost with class weighting and cross-validation.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import joblib

# Add backend to path for database access
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection

# ML imports
from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    roc_curve, precision_score, recall_score, f1_score
)
import xgboost as xgb

load_dotenv(ROOT / "backend" / ".env")


# Feature columns to use (exclude session_id, label, created_at, device_type)
FEATURE_COLUMNS = [
    'avg_mouse_vel',
    'std_mouse_vel',
    'max_mouse_vel',
    'total_distance',
    'avg_angle_change',
    'click_count',
    'avg_click_interval',
    'avg_iki',
    'std_iki',
    'avg_hold',
    'scroll_count',
    'avg_scroll_vel',
    'session_duration',
    'event_count'
]


def load_data():
    """Load session features from PostgreSQL (desktop only)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                session_id,
                avg_mouse_vel,
                std_mouse_vel,
                max_mouse_vel,
                total_distance,
                avg_angle_change,
                click_count,
                avg_click_interval,
                avg_iki,
                std_iki,
                avg_hold,
                scroll_count,
                avg_scroll_vel,
                session_duration,
                event_count,
                device_type,
                label
            FROM session_features
            WHERE device_type = 'desktop'
            AND label IS NOT NULL
            AND event_count > 0
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        df = pd.DataFrame(rows, columns=columns)
        cursor.close()
        
        print(f"Loaded {len(df)} desktop sessions")
        print(f"Label distribution:\n{df['label'].value_counts()}")
        
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        raise
    finally:
        release_connection(conn)


def preprocess_data(df):
    """Preprocess data: handle missing values, encode labels."""
    # Replace None/NaN with 0 for numeric features
    df = df.fillna(0)
    
    # Encode labels: human=0, bot=1
    df['label_encoded'] = df['label'].map({'human': 0, 'bot': 1})
    
    # Verify encoding
    if df['label_encoded'].isnull().any():
        print("Warning: Some labels could not be encoded")
        print(df['label'].unique())
    
    return df


def split_data(df):
    """Split data into train and test sets with stratification."""
    X = df[FEATURE_COLUMNS]
    y = df['label_encoded']
    
    # Stratified split: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Train set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Train label distribution:\n{y_train.value_counts()}")
    print(f"Test label distribution:\n{y_test.value_counts()}")
    
    return X_train, X_test, y_train, y_test


def scale_features(X_train, X_test):
    """Standardize features using StandardScaler."""
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, scaler


def train_random_forest(X_train, y_train):
    """Train Random Forest with class weighting and hyperparameter tuning."""
    print("\n=== Training Random Forest ===")
    
    # Base model with class weighting
    rf = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    
    # Hyperparameter search space
    param_dist = {
        'n_estimators': [50, 100, 200, 300],
        'max_depth': [5, 10, 15, 20, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2']
    }
    
    # Randomized search with cross-validation
    rf_search = RandomizedSearchCV(
        rf, param_distributions=param_dist,
        n_iter=50, cv=5, scoring='f1',
        random_state=42, n_jobs=-1, verbose=1
    )
    
    rf_search.fit(X_train, y_train)
    
    print(f"Best RF params: {rf_search.best_params_}")
    print(f"Best RF CV F1: {rf_search.best_score_:.4f}")
    
    return rf_search.best_estimator_


def train_xgboost(X_train, y_train):
    """Train XGBoost with class weighting and hyperparameter tuning."""
    print("\n=== Training XGBoost ===")
    
    # Calculate class weights for imbalance
    scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)
    print(f"Scale positive weight: {scale_pos_weight:.2f}")
    
    # Base model
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        eval_metric='logloss',
        n_jobs=-1
    )
    
    # Hyperparameter search space
    param_dist = {
        'n_estimators': [50, 100, 200, 300],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'max_depth': [3, 5, 7, 10],
        'subsample': [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0],
        'min_child_weight': [1, 3, 5]
    }
    
    # Randomized search with cross-validation
    xgb_search = RandomizedSearchCV(
        xgb_model, param_distributions=param_dist,
        n_iter=50, cv=5, scoring='f1',
        random_state=42, n_jobs=-1, verbose=1
    )
    
    xgb_search.fit(X_train, y_train)
    
    print(f"Best XGBoost params: {xgb_search.best_params_}")
    print(f"Best XGBoost CV F1: {xgb_search.best_score_:.4f}")
    
    return xgb_search.best_estimator_


def evaluate_model(model, X_test, y_test, model_name):
    """Evaluate model and return metrics."""
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"\n=== {model_name} Test Results ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
    
    metrics = {
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'roc_auc': float(roc_auc),
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y_test, y_pred, output_dict=True)
    }
    
    return metrics


def cross_validate_model(model, X_train, y_train, model_name):
    """Perform stratified 5-fold cross-validation."""
    print(f"\n=== {model_name} 5-Fold Cross-Validation ===")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    cv_scores = {
        'precision': [],
        'recall': [],
        'f1': [],
        'roc_auc': []
    }
    
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
        y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
        
        model_fold = type(model)(**model.get_params())
        model_fold.fit(X_fold_train, y_fold_train)
        
        y_pred = model_fold.predict(X_fold_val)
        y_pred_proba = model_fold.predict_proba(X_fold_val)[:, 1]
        
        cv_scores['precision'].append(precision_score(y_fold_val, y_pred))
        cv_scores['recall'].append(recall_score(y_fold_val, y_pred))
        cv_scores['f1'].append(f1_score(y_fold_val, y_pred))
        cv_scores['roc_auc'].append(roc_auc_score(y_fold_val, y_pred_proba))
    
    print(f"CV Precision: {np.mean(cv_scores['precision']):.4f} ± {np.std(cv_scores['precision']):.4f}")
    print(f"CV Recall: {np.mean(cv_scores['recall']):.4f} ± {np.std(cv_scores['recall']):.4f}")
    print(f"CV F1: {np.mean(cv_scores['f1']):.4f} ± {np.std(cv_scores['f1']):.4f}")
    print(f"CV ROC-AUC: {np.mean(cv_scores['roc_auc']):.4f} ± {np.std(cv_scores['roc_auc']):.4f}")
    
    return cv_scores


def get_feature_importance(model, feature_names):
    """Get feature importance from model."""
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    else:
        # For XGBoost
        importance = model.get_booster().get_score(importance_type='gain')
        # Map to feature names
        importance_dict = {f: importance.get(f'f{i}', 0) for i, f in enumerate(feature_names)}
        importance = [importance_dict[f] for f in feature_names]
    
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    return feature_importance


def save_artifacts(model, scaler, metrics, feature_importance, model_name):
    """Save model, scaler, metrics, and feature importance."""
    artifacts_dir = ROOT / "ml" / "models" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save model
    model_path = artifacts_dir / f"{model_name}_{timestamp}.pkl"
    joblib.dump(model, model_path)
    print(f"Saved model to {model_path}")
    
    # Save scaler
    scaler_path = artifacts_dir / f"scaler_{timestamp}.pkl"
    joblib.dump(scaler, scaler_path)
    print(f"Saved scaler to {scaler_path}")
    
    # Save metrics
    metrics_path = artifacts_dir / f"{model_name}_metrics_{timestamp}.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics to {metrics_path}")
    
    # Save feature importance
    importance_path = artifacts_dir / f"{model_name}_feature_importance_{timestamp}.csv"
    feature_importance.to_csv(importance_path, index=False)
    print(f"Saved feature importance to {importance_path}")
    
    return {
        'model_path': str(model_path),
        'scaler_path': str(scaler_path),
        'metrics_path': str(metrics_path),
        'importance_path': str(importance_path)
    }


def main():
    """Main training pipeline."""
    print("=" * 60)
    print("PHASE 7: Model Training (V1)")
    print("=" * 60)
    
    # Load data
    df = load_data()
    
    # Preprocess
    df = preprocess_data(df)
    
    # Split data
    X_train, X_test, y_train, y_test = split_data(df)
    
    # Scale features
    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)
    
    # Train Random Forest
    rf_model = train_random_forest(X_train_scaled, y_train)
    rf_cv_scores = cross_validate_model(rf_model, X_train_scaled, y_train, "Random Forest")
    rf_metrics = evaluate_model(rf_model, X_test_scaled, y_test, "Random Forest")
    rf_importance = get_feature_importance(rf_model, FEATURE_COLUMNS)
    print(f"\nRandom Forest Feature Importance:\n{rf_importance}")
    rf_artifacts = save_artifacts(rf_model, scaler, rf_metrics, rf_importance, "random_forest")
    
    # Train XGBoost
    xgb_model = train_xgboost(X_train_scaled, y_train)
    xgb_cv_scores = cross_validate_model(xgb_model, X_train_scaled, y_train, "XGBoost")
    xgb_metrics = evaluate_model(xgb_model, X_test_scaled, y_test, "XGBoost")
    xgb_importance = get_feature_importance(xgb_model, FEATURE_COLUMNS)
    print(f"\nXGBoost Feature Importance:\n{xgb_importance}")
    xgb_artifacts = save_artifacts(xgb_model, scaler, xgb_metrics, xgb_importance, "xgboost")
    
    # Compare models
    print("\n" + "=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)
    print(f"Random Forest - F1: {rf_metrics['f1']:.4f}, ROC-AUC: {rf_metrics['roc_auc']:.4f}")
    print(f"XGBoost - F1: {xgb_metrics['f1']:.4f}, ROC-AUC: {xgb_metrics['roc_auc']:.4f}")
    
    # Select best model based on F1 score
    best_model_name = "random_forest" if rf_metrics['f1'] > xgb_metrics['f1'] else "xgboost"
    print(f"\nBest model: {best_model_name}")
    
    # Save comparison summary
    comparison = {
        'random_forest': {
            'test_metrics': rf_metrics,
            'cv_scores': {k: {'mean': float(np.mean(v)), 'std': float(np.std(v))} for k, v in rf_cv_scores.items()},
            'artifacts': rf_artifacts
        },
        'xgboost': {
            'test_metrics': xgb_metrics,
            'cv_scores': {k: {'mean': float(np.mean(v)), 'std': float(np.std(v))} for k, v in xgb_cv_scores.items()},
            'artifacts': xgb_artifacts
        },
        'best_model': best_model_name,
        'timestamp': datetime.now().isoformat()
    }
    
    comparison_path = ROOT / "ml" / "models" / "artifacts" / f"model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(comparison_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"Saved comparison to {comparison_path}")
    
    print("\nTraining complete!")


if __name__ == "__main__":
    main()
