"""
One-off: split the long-running orphan session 569535c3 (accumulated across
many manual form-fills in one browser tab, sessionStorage never cleared)
into distinct real human submit attempts, using BUTTON-click timestamps as
ground-truth boundaries (same methodology as the earlier 35b2fb6d split).

Each segment becomes its own real `sessions` row + copied `events` rows (not
a hand-inserted session_features row) so a future --rebuild recomputes it
correctly instead of destroying it.
"""
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values, Json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(ROOT), "sdk-backend", ".env"))

ORPHAN_SESSION_ID = "569535c3-280e-4cbf-9fb5-745ae906ac31"
PROJECT_ID = "9f394e57-1566-4400-8c7b-10791253c9c6"
API_KEY_ID = "3876f18a-8f7f-4d86-a8be-6e369dfde676"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

EVENT_COLUMNS = [
    "event_type", "t", "x", "y", "dist", "ang", "vel", "total_dist",
    "target", "click_interval", "is_double", "tw", "th", "k", "iki", "hold",
    "scroll_y", "scroll_vel", "scroll_rev", "scroll_pause", "state", "action",
    "force", "duration", "gesture", "swipe_dist", "swipe_vel", "payload",
    "hover_duration", "overshoot_ratio",
]


def main():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute(
        f"SELECT {', '.join(EVENT_COLUMNS)} FROM public.events "
        "WHERE session_id = %s ORDER BY t ASC",
        (ORPHAN_SESSION_ID,),
    )
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} raw events from orphan session")

    t_idx = EVENT_COLUMNS.index("t")
    type_idx = EVENT_COLUMNS.index("event_type")
    target_idx = EVENT_COLUMNS.index("target")

    boundaries = [
        r[t_idx] for r in rows
        if r[type_idx] == "cl" and r[target_idx] == "BUTTON"
    ]
    print(f"Found {len(boundaries)} submit-button click boundaries")

    segments = []
    prev_t = None
    for b in boundaries:
        seg = [r for r in rows if (prev_t is None or r[t_idx] > prev_t) and r[t_idx] <= b]
        if seg:
            segments.append(seg)
        prev_t = b

    print(f"Built {len(segments)} non-empty segments")

    created = 0
    for i, seg in enumerate(segments):
        new_id = str(uuid.uuid4())
        ts = [r[t_idx] for r in seg]
        started_at = datetime.fromtimestamp(min(ts) / 1000, tz=timezone.utc)
        ended_at = datetime.fromtimestamp(max(ts) / 1000, tz=timezone.utc)

        cur.execute(
            """
            INSERT INTO public.sessions
                (id, project_id, device_type, user_agent, started_at, ended_at,
                 label, event_count, webdriver_flag, api_key_id)
            VALUES (%s, %s, 'desktop', %s, %s, %s, 'human', %s, false, %s)
            """,
            (new_id, PROJECT_ID, USER_AGENT, started_at, ended_at, len(seg), API_KEY_ID),
        )

        payload_idx = EVENT_COLUMNS.index("payload")
        insert_cols = ["session_id", *EVENT_COLUMNS]
        values = [
            (new_id, *r[:payload_idx],
             Json(r[payload_idx]) if r[payload_idx] is not None else None,
             *r[payload_idx + 1:])
            for r in seg
        ]
        execute_values(
            cur,
            f"INSERT INTO public.events ({', '.join(insert_cols)}) VALUES %s",
            values,
        )

        conn.commit()
        created += 1
        print(f"  segment {i+1}/{len(segments)}: session {new_id[:8]}... "
              f"{len(seg)} events, {(max(ts)-min(ts))/1000:.1f}s span")

    print(f"\nDone. Created {created} new labeled human sessions with real backing events.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
