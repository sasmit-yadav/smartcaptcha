import os
import sys
import argparse
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# ----------------------------
# Setup paths
# ----------------------------
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, init_db, release_connection
from features.feature_columns import FEATURE_COLUMNS

load_dotenv(ROOT / ".env")


class FeatureExtractor:
    def __init__(self):
        self.conn = get_connection()
        print("[Extractor] DB connection established")

    def get_pending_sessions(self, rebuild=False):
        """
        Sessions eligible for the training set.

        Two filters matter beyond "has a label and real events":
        - s.label IN ('bot', 'human') — not just "IS NOT NULL". Ground-truth
          labels from the dedicated bot-simulation/demo-site pipeline use
          'bot'/'human'. Live /api/predict traffic gets labeled with the
          model's own guess ('allow'/'block') by insert_session_prediction —
          training on that would mean training the model on its own past
          predictions, silently, for any customer whose SDK sends real
          telemetry (the normal case). Excluding anything outside
          ('bot', 'human') keeps live traffic out regardless of key type.
        - api_keys.key_type NOT IN ('test', 'admin') — belt-and-suspenders
          exclusion of manual/dev/test-key traffic even on the rare chance
          it ever gets inserted with a 'bot'/'human' label directly.
        """
        cursor = self.conn.cursor()

        base_filter = """
            WHERE s.label IN ('bot', 'human')
            AND s.event_count > 0
            AND (ak.key_type IS NULL OR ak.key_type NOT IN ('test', 'admin'))
        """

        if rebuild:
            cursor.execute(f"""
                SELECT s.id, s.started_at, s.ended_at,
                       s.event_count, s.device_type, s.label, s.webdriver_flag
                FROM sessions s
                LEFT JOIN api_keys ak ON s.api_key_id = ak.id
                {base_filter}
            """)
        else:
            cursor.execute(f"""
                SELECT s.id, s.started_at, s.ended_at,
                       s.event_count, s.device_type, s.label, s.webdriver_flag
                FROM sessions s
                LEFT JOIN session_features sf ON s.id = sf.session_id
                LEFT JOIN api_keys ak ON s.api_key_id = ak.id
                {base_filter}
                AND sf.session_id IS NULL
            """)

        sessions = cursor.fetchall()
        cursor.close()
        return sessions

    def get_events(self, session_id):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT event_type, t, x, y, dist, ang, vel, total_dist,
                   click_interval, iki, hold,
                   scroll_vel, scroll_rev, scroll_pause, is_double, k,
                   hover_duration, overshoot_ratio
            FROM events
            WHERE session_id = %s
            ORDER BY t ASC
        """, (session_id,))

        rows = cursor.fetchall()
        cursor.close()
        return rows


def split_events(rows):
    mouse = []
    clicks = []
    keys = []
    scrolls = []
    focus = []
    touch = []

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
        elif etype == "fv":
            focus.append(row)
        elif etype == "tc":
            touch.append(row)

    return mouse, clicks, keys, scrolls, focus, touch


def safe_mean(values):
    return float(np.mean(values)) if values else 0.0


def safe_std(values):
    return float(np.std(values)) if values else 0.0


def safe_max(values):
    return float(np.max(values)) if values else 0.0


def safe_min(values):
    return float(np.min(values)) if values else 0.0


def safe_percentile(values, percentile):
    return float(np.percentile(values, percentile)) if values else 0.0


def calculate_movement_entropy(mouse, clicks, keys):
    """Calculate entropy of movement timing and angle changes."""
    if not mouse:
        return 0.0
    
    # Get timing intervals between events
    all_events = []
    for row in mouse:
        all_events.append(('mm', row[1]))  # event_type, timestamp
    for row in clicks:
        all_events.append(('cl', row[1]))
    for row in keys:
        all_events.append(('key', row[1]))
    
    # Sort by timestamp
    all_events.sort(key=lambda x: x[1])
    
    # Calculate intervals
    intervals = []
    for i in range(1, len(all_events)):
        if all_events[i][1] is not None and all_events[i-1][1] is not None:
            intervals.append(all_events[i][1] - all_events[i-1][1])
    
    if not intervals:
        return 0.0
    
    # Calculate entropy of intervals
    hist, _ = np.histogram(intervals, bins=20, density=True)
    hist = hist[hist > 0]  # Remove zero probabilities
    entropy = -np.sum(hist * np.log(hist + 1e-10))
    
    return float(entropy)


def count_gaps(rows, threshold_ms=1000):
    timestamps = [r[1] for r in rows if r[1] is not None]
    if len(timestamps) < 2:
        return 0
    return sum(1 for i in range(1, len(timestamps)) if timestamps[i] - timestamps[i - 1] >= threshold_ms)


def compute_mouse_features(mouse):
    if not mouse:
        return {
            "avg_mouse_vel": 0.0,
            "std_mouse_vel": 0.0,
            "max_mouse_vel": 0.0,
            "total_distance": 0.0,
            "avg_angle_change": 0.0,
            "mouse_vel_p10": 0.0,
            "mouse_vel_p50": 0.0,
            "mouse_vel_p90": 0.0,
            "mouse_accel_mean": 0.0,
            "mouse_accel_std": 0.0,
            "mouse_accel_max": 0.0,
            "mouse_angle_std": 0.0,
            "mouse_angle_p90": 0.0,
            "mouse_path_efficiency": 0.0,
            "mouse_idle_gap_count": 0,
            "mouse_curvature_std": 0.0,
            "mouse_jerk_std": 0.0,
        }

    velocities = [r[6] for r in mouse if r[6] is not None]
    angles = [r[5] for r in mouse if r[5] is not None]
    distances = [r[7] for r in mouse if r[7] is not None]

    accelerations = []
    jerks = []
    for i in range(1, len(mouse)):
        prev_t, curr_t = mouse[i - 1][1], mouse[i][1]
        prev_v, curr_v = mouse[i - 1][6], mouse[i][6]
        if prev_t is None or curr_t is None or prev_v is None or curr_v is None:
            continue
        dt_seconds = (curr_t - prev_t) / 1000
        if dt_seconds > 0:
            accel = abs(curr_v - prev_v) / dt_seconds
            accelerations.append(accel)
            
            # Calculate jerk (rate of change of acceleration)
            if i > 1 and len(accelerations) >= 2:
                prev_accel = accelerations[-2]
                if dt_seconds > 0:
                    jerk = abs(accel - prev_accel) / dt_seconds
                    jerks.append(jerk)

    coords = [(r[2], r[3]) for r in mouse if r[2] is not None and r[3] is not None]
    total_distance = safe_max(distances)
    direct_distance = 0.0
    if len(coords) >= 2:
        dx = coords[-1][0] - coords[0][0]
        dy = coords[-1][1] - coords[0][1]
        direct_distance = float(np.sqrt(dx * dx + dy * dy))
    path_efficiency = direct_distance / total_distance if total_distance > 0 else 0.0

    # Calculate curvature std (variation in angle changes)
    curvature_std = safe_std(angles)

    return {
        "avg_mouse_vel": safe_mean(velocities),
        "std_mouse_vel": safe_std(velocities),
        "max_mouse_vel": safe_max(velocities),
        "total_distance": total_distance,
        "avg_angle_change": safe_mean(angles),
        "mouse_vel_p10": safe_percentile(velocities, 10),
        "mouse_vel_p50": safe_percentile(velocities, 50),
        "mouse_vel_p90": safe_percentile(velocities, 90),
        "mouse_accel_mean": safe_mean(accelerations),
        "mouse_accel_std": safe_std(accelerations),
        "mouse_accel_max": safe_max(accelerations),
        "mouse_angle_std": safe_std(angles),
        "mouse_angle_p90": safe_percentile(angles, 90),
        "mouse_path_efficiency": path_efficiency,
        "mouse_idle_gap_count": count_gaps(mouse),
        "mouse_curvature_std": curvature_std,
        "mouse_jerk_std": safe_std(jerks),
    }


def compute_click_features(clicks):
    intervals = [r[8] for r in clicks if r[8] is not None]
    hover_durations = [r[15] for r in clicks if r[15] is not None]  # V2 telemetry
    overshoot_ratios = [r[16] for r in clicks if r[16] is not None]  # V2 telemetry

    return {
        "click_count": len(clicks),
        "avg_click_interval": safe_mean(intervals),
        "click_interval_std": safe_std(intervals),
        "click_interval_min": safe_min(intervals),
        "click_interval_p90": safe_percentile(intervals, 90),
        "double_click_count": sum(1 for r in clicks if r[14]),
        "avg_hover_duration": safe_mean(hover_durations),  # V2 telemetry
        "hover_duration_std": safe_std(hover_durations),  # V2 telemetry
        "avg_overshoot_ratio": safe_mean(overshoot_ratios),  # V2 telemetry
        "overshoot_ratio_std": safe_std(overshoot_ratios),  # V2 telemetry
    }


def compute_keyboard_features(keys):
    ikis = [r[9] for r in keys if r[9] is not None]
    holds = [r[10] for r in keys if r[10] is not None]

    return {
        "avg_iki": safe_mean(ikis),
        "std_iki": safe_std(ikis),
        "avg_hold": safe_mean(holds),
        "key_count": len(keys),
        "iki_p10": safe_percentile(ikis, 10),
        "iki_p50": safe_percentile(ikis, 50),
        "iki_p90": safe_percentile(ikis, 90),
        "hold_std": safe_std(holds),
        "hold_p90": safe_percentile(holds, 90),
        "backspace_count": sum(1 for r in keys if r[15] == "Backspace"),
    }


def compute_scroll_features(scrolls):
    velocities = [r[11] for r in scrolls if r[11] is not None]

    return {
        "scroll_count": len(scrolls),
        "avg_scroll_vel": safe_mean(velocities),
        "scroll_vel_std": safe_std(velocities),
        "scroll_rev_count": sum(1 for r in scrolls if r[12]),
        "scroll_pause_count": sum(1 for r in scrolls if r[13]),
    }


def insert_features(conn, row, rebuild=False):
    cursor = conn.cursor()

    try:
        if rebuild:
            cursor.execute("DELETE FROM session_features WHERE session_id = %s", (row[0],))
        columns = ["session_id", *FEATURE_COLUMNS, "device_type", "label"]
        placeholders = ",".join(["%s"] * len(columns))
        column_sql = ",".join(columns)
        cursor.execute(
            f"INSERT INTO session_features ({column_sql}) VALUES ({placeholders})",
            row,
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[Insert Error]", e)
        raise
    finally:
        cursor.close()


def process_sessions(rebuild=False):
    extractor = None

    try:
        print("Starting feature extraction...")
        init_db()
        extractor = FeatureExtractor()

        sessions = extractor.get_pending_sessions(rebuild=rebuild)
        print(f"Found {len(sessions)} pending sessions")

        for session in sessions:
            session_id, started_at, ended_at, event_count, device_type, label, webdriver_flag = session
            print(f"Processing session: {session_id[:8]}...")

            rows = extractor.get_events(session_id)
            mouse, clicks, keys, scrolls, focus, touch = split_events(rows)

            features = {}
            features.update(compute_mouse_features(mouse))
            features.update(compute_click_features(clicks))
            features.update(compute_keyboard_features(keys))
            features.update(compute_scroll_features(scrolls))

            session_duration = 0
            if started_at and ended_at:
                session_duration = (ended_at - started_at).total_seconds()

            features["session_duration"] = float(session_duration or 0)
            features["event_count"] = int(event_count or len(rows))
            features["mouse_event_ratio"] = len(mouse) / len(rows) if rows else 0.0
            features["focus_event_count"] = len(focus)
            features["touch_event_count"] = len(touch)
            features["event_rate"] = len(rows) / session_duration if session_duration > 0 else 0.0
            features["pause_count"] = count_gaps(rows)
            features["pause_ratio"] = features["pause_count"] / max(len(rows) - 1, 1)
            features["movement_entropy"] = calculate_movement_entropy(mouse, clicks, keys)
            features["webdriver_flag"] = webdriver_flag or False

            feature_row = (
                session_id,
                *[features.get(column, 0) for column in FEATURE_COLUMNS],
                device_type,
                label,
            )

            insert_features(extractor.conn, feature_row, rebuild=rebuild)

        print("Feature extraction completed successfully")

    except Exception as e:
        print("[FATAL ERROR]", e)

    finally:
        if extractor:
            release_connection(extractor.conn)
            print("DB connection closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract V2 ML features from labeled sessions")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Recompute features for all labeled sessions instead of only new sessions",
    )
    args = parser.parse_args()
    process_sessions(rebuild=args.rebuild)
