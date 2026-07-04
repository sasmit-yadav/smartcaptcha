"""Stage 1B: Feature Distribution Analysis - Compare human vs bot distributions."""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, init_db, release_connection
from features.feature_columns import FEATURE_COLUMNS

load_dotenv(ROOT / ".env")


def load_all_sessions():
    """Load all sessions from database."""
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
    
    print(f"Loaded {len(df)} total sessions")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    return df


def analyze_feature_separation(df):
    """Analyze how well each feature separates humans from bots."""
    human_df = df[df['label'] == 'human']
    bot_df = df[df['label'] == 'bot']
    
    separation_scores = []
    
    for feature in FEATURE_COLUMNS:
        human_values = human_df[feature].dropna()
        bot_values = bot_df[feature].dropna()
        
        # Calculate overlap metrics
        human_mean = human_values.mean()
        human_std = human_values.std()
        bot_mean = bot_values.mean()
        bot_std = bot_values.std()
        
        # Cohen's d (effect size)
        pooled_std = np.sqrt((human_std**2 + bot_std**2) / 2)
        cohens_d = abs(bot_mean - human_mean) / pooled_std if pooled_std > 0 else 0
        
        # Overlap coefficient
        if human_std > 0 and bot_std > 0:
            overlap = 0
        else:
            overlap = 1  # No separation if no variance
        
        separation_scores.append({
            'feature': feature,
            'human_mean': human_mean,
            'human_std': human_std,
            'bot_mean': bot_mean,
            'bot_std': bot_std,
            'cohens_d': cohens_d,
            'separation': 'high' if cohens_d > 0.8 else 'medium' if cohens_d > 0.5 else 'low' if cohens_d > 0.2 else 'none'
        })
    
    separation_df = pd.DataFrame(separation_scores)
    separation_df = separation_df.sort_values('cohens_d', ascending=False)
    
    return separation_df


def plot_feature_distributions(df, separation_df, output_dir):
    """Generate distribution plots for top features."""
    human_df = df[df['label'] == 'human']
    bot_df = df[df['label'] == 'bot']
    
    # Plot top 15 features by separation
    top_features = separation_df.head(15)['feature'].tolist()
    
    fig, axes = plt.subplots(5, 3, figsize=(15, 20))
    axes = axes.flatten()
    
    for idx, feature in enumerate(top_features):
        ax = axes[idx]
        
        # Plot histograms
        ax.hist(human_df[feature].dropna(), alpha=0.5, label='Human', bins=20, color='blue')
        ax.hist(bot_df[feature].dropna(), alpha=0.5, label='Bot', bins=20, color='red')
        
        ax.set_xlabel(feature)
        ax.set_ylabel('Frequency')
        ax.set_title(f"{feature} (d={separation_df[separation_df['feature']==feature]['cohens_d'].values[0]:.2f})")
        ax.legend()
    
    plt.tight_layout()
    plot_path = output_dir / "feature_distributions.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Saved distribution plots to {plot_path}")
    plt.close()


def identify_problematic_features(separation_df):
    """Identify useless and potentially leaking features."""
    print(f"\n{'='*60}")
    print(f"FEATURE SEPARATION ANALYSIS")
    print(f"{'='*60}")
    
    # Useless features (low separation)
    useless = separation_df[separation_df['separation'] == 'none']
    print(f"\n⚠️  USELESS FEATURES (no separation): {len(useless)}")
    for _, row in useless.iterrows():
        print(f"   - {row['feature']}: d={row['cohens_d']:.3f}")
    
    # Low separation features
    low_sep = separation_df[separation_df['separation'] == 'low']
    print(f"\n⚠️  LOW SEPARATION FEATURES: {len(low_sep)}")
    for _, row in low_sep.iterrows():
        print(f"   - {row['feature']}: d={row['cohens_d']:.3f}")
    
    # High separation features (potential leakage)
    high_sep = separation_df[separation_df['separation'] == 'high']
    print(f"\n🔍 HIGH SEPARATION FEATURES (potential leakage): {len(high_sep)}")
    for _, row in high_sep.head(10).iterrows():
        print(f"   - {row['feature']}: d={row['cohens_d']:.3f}")
        print(f"     Human: {row['human_mean']:.2f}±{row['human_std']:.2f}")
        print(f"     Bot: {row['bot_mean']:.2f}±{row['bot_std']:.2f}")
    
    # Specifically check event_count and session_duration
    print(f"\n{'='*60}")
    print(f"SUSPICIOUS FEATURES CHECK")
    print(f"{'='*60}")
    
    suspicious_features = ['event_count', 'session_duration', 'total_distance']
    for feature in suspicious_features:
        if feature in separation_df['feature'].values:
            row = separation_df[separation_df['feature'] == feature].iloc[0]
            print(f"\n{feature}:")
            print(f"  Cohen's d: {row['cohens_d']:.3f}")
            print(f"  Separation: {row['separation']}")
            print(f"  Human: {row['human_mean']:.2f}±{row['human_std']:.2f}")
            print(f"  Bot: {row['bot_mean']:.2f}±{row['bot_std']:.2f}")
            
            if row['separation'] == 'high':
                print(f"  ⚠️  WARNING: High separation may indicate shortcut learning")
            elif row['separation'] == 'none':
                print(f"  ⚠️  WARNING: No separation - feature may be useless")


def save_analysis_results(separation_df, output_dir):
    """Save separation analysis results."""
    output_path = output_dir / "feature_separation_analysis.csv"
    separation_df.to_csv(output_path, index=False)
    print(f"\nSaved separation analysis to {output_path}")


def main():
    print("="*60)
    print("STAGE 1B: FEATURE DISTRIBUTION ANALYSIS")
    print("="*60)
    
    # Load data
    df = load_all_sessions()
    
    # Analyze feature separation
    separation_df = analyze_feature_separation(df)
    
    # Create output directory
    output_dir = ROOT / "ml" / "models" / "artifacts" / "baseline_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plots
    plot_feature_distributions(df, separation_df, output_dir)
    
    # Identify problematic features
    identify_problematic_features(separation_df)
    
    # Save results
    save_analysis_results(separation_df, output_dir)
    
    print("\n" + "="*60)
    print("Analysis complete")
    print("="*60)


if __name__ == "__main__":
    main()
