"""
Export session features to CSV for model training.
"""
import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection

load_dotenv(ROOT / "backend" / ".env")


def export_features_to_csv():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get all features with labels
        cursor.execute("""
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
            WHERE label IS NOT NULL
        """)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # Create CSV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = ROOT / "ml" / f"features_{timestamp}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        print(f"Exported {len(rows)} features to {output_file}")
        
        # Show label distribution
        cursor.execute("""
            SELECT label, COUNT(*) 
            FROM session_features
            WHERE label IS NOT NULL
            GROUP BY label
        """)
        label_counts = cursor.fetchall()
        print("\nLabel distribution:")
        for label, count in label_counts:
            print(f"  {label}: {count}")
        
        cursor.close()
        
    except Exception as e:
        print(f"Error exporting features: {e}")
    finally:
        release_connection(conn)


if __name__ == "__main__":
    export_features_to_csv()
