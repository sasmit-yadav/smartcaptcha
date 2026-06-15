import os
import sys
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# ----------------------------
# Setup paths
# ----------------------------
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from core.database import get_connection, release_connection

load_dotenv(ROOT / "backend" / ".env")


class FeatureExtractor:
    def __init__(self):
        self.conn = get_connection()
        print("[Extractor] DB connection established")

    def get_pending_sessions(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT s.id, s.started_at, s.ended_at,
                   s.event_count, s.device_type, s.label
            FROM sessions s
            LEFT JOIN session_features sf
            ON s.id = sf.session_id
            WHERE sf.session_id IS NULL
            AND s.label IS NOT NULL
            AND s.event_count > 0
        """)

        sessions = cursor.fetchall()
        cursor.close()
        return sessions

    def get_events(self, session_id):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT event_type, dist, ang, vel, total_dist,
                   click_interval, iki, hold,
                   scroll_vel, scroll_rev, scroll_pause
            FROM events
            WHERE session_id = %s
        """, (session_id,))

        rows = cursor.fetchall()
        cursor.close()
        return rows


def split_events(rows):
    mouse = []
    clicks = []
    keys = []
    scrolls = []

    for row in rows:
        etype = row[0]

        if etype == "mm":
            mouse.append(row)
        elif etype == "cl":
            clicks.append(row)
        elif etype in ["kd", "ku"]:
            keys.append(row)
        elif etype == "sc":
            scrolls.append(row)

    return mouse, clicks, keys, scrolls


def compute_mouse_features(mouse):
    if not mouse:
        return 0, 0, 0, 0, 0

    velocities = [r[3] for r in mouse if r[3] is not None]
    angles = [r[2] for r in mouse if r[2] is not None]
    distances = [r[4] for r in mouse if r[4] is not None]

    avg_vel = float(np.mean(velocities)) if velocities else 0
    std_vel = float(np.std(velocities)) if velocities else 0
    max_vel = float(np.max(velocities)) if velocities else 0
    total_distance = float(np.max(distances)) if distances else 0

    angle_changes = []
    for i in range(1, len(angles)):
        angle_changes.append(abs(angles[i] - angles[i - 1]))

    avg_angle_change = float(np.mean(angle_changes)) if angle_changes else 0

    return avg_vel, std_vel, max_vel, total_distance, avg_angle_change


def compute_click_features(clicks):
    click_count = len(clicks)
    intervals = [r[5] for r in clicks if r[5] is not None]
    avg_click_interval = float(np.mean(intervals)) if intervals else 0

    return click_count, avg_click_interval


def compute_keyboard_features(keys):
    ikis = [r[6] for r in keys if r[6] is not None]
    holds = [r[7] for r in keys if r[7] is not None]

    avg_iki = float(np.mean(ikis)) if ikis else 0
    std_iki = float(np.std(ikis)) if ikis else 0
    avg_hold = float(np.mean(holds)) if holds else 0

    return avg_iki, std_iki, avg_hold


def compute_scroll_features(scrolls):
    scroll_count = len(scrolls)
    velocities = [r[8] for r in scrolls if r[8] is not None]
    avg_scroll_vel = float(np.mean(velocities)) if velocities else 0

    return scroll_count, avg_scroll_vel


def insert_features(conn, row):
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO session_features (
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
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, row)

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[Insert Error]", e)
        raise
    finally:
        cursor.close()


def process_sessions():
    extractor = None

    try:
        print("Starting feature extraction...")
        extractor = FeatureExtractor()

        sessions = extractor.get_pending_sessions()
        print(f"Found {len(sessions)} pending sessions")

        for session in sessions:
            session_id, started_at, ended_at, event_count, device_type, label = session
            print(f"Processing session: {session_id[:8]}...")

            rows = extractor.get_events(session_id)
            mouse, clicks, keys, scrolls = split_events(rows)

            avg_mouse_vel, std_mouse_vel, max_mouse_vel, total_distance, avg_angle_change = compute_mouse_features(mouse)
            click_count, avg_click_interval = compute_click_features(clicks)
            avg_iki, std_iki, avg_hold = compute_keyboard_features(keys)
            scroll_count, avg_scroll_vel = compute_scroll_features(scrolls)

            session_duration = 0
            if started_at and ended_at:
                session_duration = (ended_at - started_at).total_seconds()

            feature_row = (
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
            )

            insert_features(extractor.conn, feature_row)

        print("Feature extraction completed successfully")

    except Exception as e:
        print("[FATAL ERROR]", e)

    finally:
        if extractor:
            release_connection(extractor.conn)
            print("DB connection closed")


if __name__ == "__main__":
    process_sessions()