"""
Test inference with actual human and bot session features from database.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection
from models.inference import predict_session

load_dotenv(ROOT / "backend" / ".env")


def get_session_features(session_id):
    """Get features for a specific session."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT 
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
                label
            FROM session_features
            WHERE session_id = %s
        """
        
        cursor.execute(query, (session_id,))
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            columns = [
                'avg_mouse_vel', 'std_mouse_vel', 'max_mouse_vel', 'total_distance',
                'avg_angle_change', 'click_count', 'avg_click_interval', 'avg_iki',
                'std_iki', 'avg_hold', 'scroll_count', 'avg_scroll_vel',
                'session_duration', 'event_count', 'label'
            ]
            features = dict(zip(columns, row))
            return features
        else:
            return None
            
    except Exception as e:
        print(f"Error getting session features: {e}")
        return None
    finally:
        release_connection(conn)


def test_actual_sessions():
    """Test inference with actual human and bot sessions."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get one human session
        cursor.execute("""
            SELECT session_id FROM session_features
            WHERE label = 'human' AND device_type = 'desktop'
            LIMIT 1
        """)
        human_session = cursor.fetchone()
        
        # Get one bot session
        cursor.execute("""
            SELECT session_id FROM session_features
            WHERE label = 'bot' AND device_type = 'desktop'
            LIMIT 1
        """)
        bot_session = cursor.fetchone()
        
        cursor.close()
        
        print("=" * 60)
        print("Testing Inference with Actual Sessions")
        print("=" * 60)
        
        if human_session:
            human_id = human_session[0]
            print(f"\nHuman Session: {human_id[:8]}...")
            human_features = get_session_features(human_id)
            if human_features:
                label = human_features.pop('label')
                print(f"Actual label: {label}")
                print(f"Features: {human_features}")
                result = predict_session(human_features)
                print(f"Prediction: {result}")
        
        if bot_session:
            bot_id = bot_session[0]
            print(f"\nBot Session: {bot_id[:8]}...")
            bot_features = get_session_features(bot_id)
            if bot_features:
                label = bot_features.pop('label')
                print(f"Actual label: {label}")
                print(f"Features: {bot_features}")
                result = predict_session(bot_features)
                print(f"Prediction: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        release_connection(conn)


if __name__ == "__main__":
    test_actual_sessions()
