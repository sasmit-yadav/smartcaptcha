"""
Evaluate trained model with detailed metrics and visualizations.
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    confusion_matrix, roc_curve, auc, 
    precision_recall_curve, classification_report
)
import joblib

ROOT = Path(__file__).resolve().parents[2]


def load_model_and_scaler(model_path, scaler_path):
    """Load trained model and scaler."""
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    return model, scaler


def plot_confusion_matrix(y_true, y_pred, model_name, save_path):
    """Plot and save confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Human', 'Bot'], yticklabels=['Human', 'Bot'])
    plt.title(f'Confusion Matrix - {model_name}')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved confusion matrix to {save_path}")


def plot_roc_curve(y_true, y_pred_proba, model_name, save_path):
    """Plot and save ROC curve."""
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.4f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(f'ROC Curve - {model_name}')
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved ROC curve to {save_path}")


def plot_precision_recall_curve(y_true, y_pred_proba, model_name, save_path):
    """Plot and save precision-recall curve."""
    precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
    pr_auc = auc(recall, precision)
    
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2, label=f'PR curve (AUC = {pr_auc:.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'Precision-Recall Curve - {model_name}')
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved precision-recall curve to {save_path}")


def plot_feature_importance(feature_importance_df, model_name, save_path):
    """Plot and save feature importance."""
    plt.figure(figsize=(10, 8))
    sns.barplot(data=feature_importance_df.head(10), x='importance', y='feature')
    plt.title(f'Top 10 Feature Importance - {model_name}')
    plt.xlabel('Importance')
    plt.ylabel('Feature')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved feature importance plot to {save_path}")


def evaluate_from_artifacts(model_path, scaler_path, X_test, y_test, model_name):
    """Evaluate model from saved artifacts."""
    model, scaler = load_model_and_scaler(model_path, scaler_path)
    
    # Scale test data
    X_test_scaled = scaler.transform(X_test)
    
    # Predictions
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Create output directory
    output_dir = ROOT / "ml" / "models" / "artifacts" / "evaluations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plots
    plot_confusion_matrix(y_test, y_pred, model_name, output_dir / f"{model_name}_confusion_matrix.png")
    plot_roc_curve(y_test, y_pred_proba, model_name, output_dir / f"{model_name}_roc_curve.png")
    plot_precision_recall_curve(y_test, y_pred_proba, model_name, output_dir / f"{model_name}_pr_curve.png")
    
    # Load and plot feature importance
    importance_path = ROOT / "ml" / "models" / "artifacts" / f"{model_name}_feature_importance_*.csv"
    importance_files = list(ROOT / "ml" / "models" / "artifacts").glob(f"{model_name}_feature_importance_*.csv")
    if importance_files:
        importance_df = pd.read_csv(importance_files[-1])
        plot_feature_importance(importance_df, model_name, output_dir / f"{model_name}_feature_importance.png")
    
    # Print classification report
    print(f"\n=== {model_name} Detailed Evaluation ===")
    print(classification_report(y_test, y_pred, target_names=['Human', 'Bot']))
    
    return {
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'classification_report': classification_report(y_test, y_pred, output_dict=True)
    }


if __name__ == "__main__":
    print("This module provides evaluation utilities. Use it from train_model.py or import functions.")
