"""Stage 1A: False Positive Analysis - Analyze humans predicted as bots."""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, init_db, release_connection
from features.feature_columns import FEATURE_COLUMNS

load_dotenv(ROOT / ".env")


def load_model_and_scaler():
    """Load the baseline V2 model and scaler."""
    artifacts_dir = ROOT / "ml" / "models" / "artifacts" / "baseline_v2"
    
    model_path = artifacts_dir / "random_forest_20260619_210124.pkl"
    scaler_path = artifacts_dir / "scaler_20260619_210124.pkl"
    metadata_path = artifacts_dir / "random_forest_metadata_20260619_210124.json"
    
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    print(f"Loaded model from {model_path}")
    print(f"Decision threshold: {metadata['decision_threshold']}")
    
    return model, scaler, metadata['decision_threshold']


def load_human_sessions():
    """Load all human sessions from database."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        selected_columns = ["session_id", *FEATURE_COLUMNS, "device_type", "label"]
        cursor.execute(
            f"""
            SELECT {", ".join(selected_columns)}
            FROM session_features
            WHERE label = 'human'
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
    
    print(f"Loaded {len(df)} human sessions")
    return df


def analyze_false_positives(model, scaler, threshold, df):
    """Identify and analyze false positives."""
    # Prepare features
    X = df[FEATURE_COLUMNS].fillna(0)
    X_scaled = scaler.transform(X)
    
    # Get predictions
    probabilities = model.predict_proba(X_scaled)[:, 1]
    predictions = (probabilities >= threshold).astype(int)
    
    # Add predictions to dataframe
    df['bot_probability'] = probabilities
    df['predicted_label'] = predictions
    df['predicted_label_str'] = df['predicted_label'].map({0: 'human', 1: 'bot'})
    
    # Identify false positives (humans predicted as bots)
    false_positives = df[df['predicted_label'] == 1].copy()
    
    print(f"\n{'='*60}")
    print(f"FALSE POSITIVE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total human sessions: {len(df)}")
    print(f"False positives (humans predicted as bots): {len(false_positives)}")
    print(f"False positive rate: {len(false_positives)/len(df)*100:.2f}%")
    
    if len(false_positives) == 0:
        print("\nNo false positives found in current dataset.")
        print("This suggests the issue may be in production with new human behavior patterns.")
        return None
    
    # Analyze characteristics
    print(f"\n{'='*60}")
    print(f"FALSE POSITIVE DETAILS")
    print(f"{'='*60}")
    
    for idx, row in false_positives.iterrows():
        print(f"\n--- Session: {row['session_id']} ---")
        print(f"Bot Probability: {row['bot_probability']:.4f}")
        print(f"Session Duration: {row['session_duration']:.2f}s")
        print(f"Event Count: {int(row['event_count'])}")
        print(f"Device Type: {row['device_type']}")
        
        # Key behavioral features
        print(f"Key Features:")
        print(f"  - Avg Mouse Vel: {row['avg_mouse_vel']:.2f}")
        print(f"  - Std Mouse Vel: {row['std_mouse_vel']:.2f}")
        print(f"  - Path Efficiency: {row['mouse_path_efficiency']:.4f}")
        print(f"  - Click Count: {int(row['click_count'])}")
        print(f"  - Key Count: {int(row['key_count'])}")
        print(f"  - Scroll Count: {int(row['scroll_count'])}")
        print(f"  - Pause Count: {int(row['pause_count'])}")
        print(f"  - Event Rate: {row['event_rate']:.2f} events/sec")
    
    # Summary statistics
    print(f"\n{'='*60}")
    print(f"FALSE POSITIVE PATTERNS")
    print(f"{'='*60}")
    
    print(f"\nSession Duration Statistics:")
    print(f"  Mean: {false_positives['session_duration'].mean():.2f}s")
    print(f"  Median: {false_positives['session_duration'].median():.2f}s")
    print(f"  Min: {false_positives['session_duration'].min():.2f}s")
    print(f"  Max: {false_positives['session_duration'].max():.2f}s")
    
    print(f"\nEvent Count Statistics:")
    print(f"  Mean: {false_positives['event_count'].mean():.0f}")
    print(f"  Median: {false_positives['event_count'].median():.0f}")
    print(f"  Min: {false_positives['event_count'].min():.0f}")
    print(f"  Max: {false_positives['event_count'].max():.0f}")
    
    print(f"\nTyping Behavior:")
    print(f"  Sessions with no typing: {sum(false_positives['key_count'] == 0)}")
    print(f"  Sessions with typing: {sum(false_positives['key_count'] > 0)}")
    
    print(f"\nMouse Behavior:")
    print(f"  Sessions with no mouse moves: {sum(false_positives['mouse_move_count'] == 0)}")
    print(f"  Sessions with mouse moves: {sum(false_positives['mouse_move_count'] > 0)}")
    
    print(f"\nScroll Behavior:")
    print(f"  Sessions with no scroll: {sum(false_positives['scroll_count'] == 0)}")
    print(f"  Sessions with scroll: {sum(false_positives['scroll_count'] > 0)}")
    
    # Check for specific patterns
    print(f"\n{'='*60}")
    print(f"PATTERN ANALYSIS")
    print(f"{'='*60}")
    
    very_short = false_positives[false_positives['session_duration'] < 5]
    if len(very_short) > 0:
        print(f"\n⚠️  Very short sessions (<5s): {len(very_short)}")
        print(f"   These may be legitimate quick interactions or incomplete sessions")
    
    no_typing = false_positives[false_positives['key_count'] == 0]
    if len(no_typing) > 0:
        print(f"\n⚠️  No typing: {len(no_typing)}")
        print(f"   May be click-only interactions (common in some workflows)")
    
    no_scroll = false_positives[false_positives['scroll_count'] == 0]
    if len(no_scroll) > 0:
        print(f"\n⚠️  No scrolling: {len(no_scroll)}")
        print(f"   May indicate above-the-fold interactions")
    
    high_efficiency = false_positives[false_positives['mouse_path_efficiency'] > 0.9]
    if len(high_efficiency) > 0:
        print(f"\n⚠️  High path efficiency (>0.9): {len(high_efficiency)}")
        print(f"   Very direct mouse movements - unusual for humans")
    
    low_pause = false_positives[false_positives['pause_count'] < 3]
    if len(low_pause) > 0:
        print(f"\n⚠️  Low pause count (<3): {len(low_pause)}")
        print(f"   Very continuous activity - unusual for humans")
    
    return false_positives


def save_results(false_positives, df):
    """Save analysis results to file."""
    results_dir = ROOT / "ml" / "models" / "artifacts" / "baseline_v2"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full dataset with predictions
    df_with_predictions = df.copy()
    output_path = results_dir / "false_positive_analysis_full.csv"
    df_with_predictions.to_csv(output_path, index=False)
    print(f"\nSaved full analysis to {output_path}")
    
    # Save false positives only
    if false_positives is not None and len(false_positives) > 0:
        fp_path = results_dir / "false_positives_only.csv"
        false_positives.to_csv(fp_path, index=False)
        print(f"Saved false positives to {fp_path}")


def main():
    print("="*60)
    print("STAGE 1A: FALSE POSITIVE ANALYSIS")
    print("="*60)
    
    # Load model and data
    model, scaler, threshold = load_model_and_scaler()
    df = load_human_sessions()
    
    # Analyze false positives
    false_positives = analyze_false_positives(model, scaler, threshold, df)
    
    # Save results
    save_results(false_positives, df)
    
    print("\n" + "="*60)
    print("Analysis complete")
    print("="*60)


if __name__ == "__main__":
    main()
