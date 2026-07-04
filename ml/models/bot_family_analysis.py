"""Stage 1C: Bot Family Labeling - Add bot_family column to dataset."""
import json
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, init_db, release_connection
from features.feature_columns import FEATURE_COLUMNS

load_dotenv(ROOT / "backend" / ".env")


def load_bot_sessions():
    """Load all bot sessions from database."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        selected_columns = ["session_id", *FEATURE_COLUMNS, "device_type", "label"]
        cursor.execute(
            f"""
            SELECT {", ".join(selected_columns)}
            FROM session_features
            WHERE label = 'bot'
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
    
    print(f"Loaded {len(df)} bot sessions")
    return df


def analyze_session_patterns(df):
    """Analyze session_id patterns and behavioral clusters."""
    print(f"\n{'='*60}")
    print(f"SESSION ID PATTERN ANALYSIS")
    print(f"{'='*60}")
    
    # Show sample session_ids
    print(f"\nSample session_ids:")
    for i, session_id in enumerate(df['session_id'].head(20)):
        print(f"  {i+1}. {session_id}")
    
    # Analyze behavioral clusters
    print(f"\n{'='*60}")
    print(f"BEHAVIORAL CLUSTER ANALYSIS")
    print(f"{'='*60}")
    
    # Cluster by key metrics
    df['velocity_cluster'] = pd.cut(df['avg_mouse_vel'], 
                                    bins=[0, 100, 500, 1000, float('inf')],
                                    labels=['very_slow', 'slow', 'medium', 'fast'])
    
    df['duration_cluster'] = pd.cut(df['session_duration'],
                                    bins=[0, 1, 5, 30, float('inf')],
                                    labels=['instant', 'very_short', 'short', 'long'])
    
    df['event_cluster'] = pd.cut(df['event_count'],
                                  bins=[0, 10, 50, 200, float('inf')],
                                  labels=['minimal', 'low', 'medium', 'high'])
    
    print(f"\nVelocity clusters:")
    print(df['velocity_cluster'].value_counts())
    
    print(f"\nDuration clusters:")
    print(df['duration_cluster'].value_counts())
    
    print(f"\nEvent clusters:")
    print(df['event_cluster'].value_counts())
    
    # Cross-tabulation
    print(f"\nVelocity x Duration cross-tab:")
    print(pd.crosstab(df['velocity_cluster'], df['duration_cluster']))
    
    return df


def label_bot_families(df):
    """Label bot sessions based on behavioral patterns."""
    print(f"\n{'='*60}")
    print(f"BOT FAMILY LABELING")
    print(f"{'='*60}")
    
    def assign_family(row):
        # Logic based on behavioral patterns
        if row['session_duration'] < 1.0:
            return 'instant_bot'
        elif row['avg_mouse_vel'] < 100:
            return 'slow_bot'
        elif row['event_count'] < 10:
            return 'minimal_bot'
        elif row['mouse_path_efficiency'] > 0.95:
            return 'efficient_bot'
        elif row['std_mouse_vel'] < 50:
            return 'consistent_bot'
        elif row['pause_count'] < 2:
            return 'continuous_bot'
        else:
            return 'other_bot'
    
    df['bot_family'] = df.apply(assign_family, axis=1)
    
    print(f"\nBot family distribution:")
    print(df['bot_family'].value_counts())
    
    # Show characteristics of each family
    print(f"\n{'='*60}")
    print(f"FAMILY CHARACTERISTICS")
    print(f"{'='*60}")
    
    for family in df['bot_family'].unique():
        family_df = df[df['bot_family'] == family]
        print(f"\n{family} (n={len(family_df)}):")
        print(f"  Avg duration: {family_df['session_duration'].mean():.2f}s")
        print(f"  Avg velocity: {family_df['avg_mouse_vel'].mean():.2f}")
        print(f"  Avg events: {family_df['event_count'].mean():.0f}")
        print(f"  Path efficiency: {family_df['mouse_path_efficiency'].mean():.3f}")
        print(f"  Std velocity: {family_df['std_mouse_vel'].mean():.2f}")
    
    return df


def save_labeled_data(df):
    """Save labeled data and create mapping file."""
    output_dir = ROOT / "ml" / "models" / "artifacts" / "baseline_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full labeled dataset
    output_path = output_dir / "bot_sessions_labeled.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved labeled bot sessions to {output_path}")
    
    # Save family mapping
    family_mapping = df[['session_id', 'bot_family']].to_dict('records')
    mapping_path = output_dir / "bot_family_mapping.json"
    with open(mapping_path, 'w') as f:
        json.dump(family_mapping, f, indent=2)
    print(f"Saved family mapping to {mapping_path}")
    
    # Save summary statistics
    summary = {}
    for family in df['bot_family'].unique():
        family_df = df[df['bot_family'] == family]
        summary[family] = {
            'count': int(len(family_df)),
            'avg_session_duration': float(family_df['session_duration'].mean()),
            'avg_mouse_vel': float(family_df['avg_mouse_vel'].mean()),
            'avg_event_count': float(family_df['event_count'].mean()),
            'avg_path_efficiency': float(family_df['mouse_path_efficiency'].mean()),
        }
    
    summary_path = output_dir / "bot_family_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved family summary to {summary_path}")


def main():
    print("="*60)
    print("STAGE 1C: BOT FAMILY LABELING")
    print("="*60)
    
    # Load bot sessions
    df = load_bot_sessions()
    
    # Analyze patterns
    df = analyze_session_patterns(df)
    
    # Label families
    df = label_bot_families(df)
    
    # Save results
    save_labeled_data(df)
    
    print("\n" + "="*60)
    print("Bot family labeling complete")
    print("="*60)


if __name__ == "__main__":
    main()
