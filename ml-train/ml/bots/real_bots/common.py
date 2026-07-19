"""
Shared helpers for the tool-diversity bots (strategy doc step 5).

Why these bots exist and how they differ from ml-train/ml/bots/*.py:

The original 8 bot classes (instant/linear/timed/smart/aggressive/stealth/
adversarial/multi_page) all fabricate their feature vectors in Python via
BaseBot.add_event() and POST them directly to /api/telemetry — the browser
page is loaded, but its own DOM-event listeners are largely bypassed; the
"bot-ness" comes entirely from hand-picked numbers, not from anything a real
automation tool actually produces. That's a valid and useful set of labeled
examples, but it cannot answer the question the strategy doc's step 5 is
actually asking: how do DIFFERENT AUTOMATION TOOLS (Selenium vs Playwright
vs a stealth-patched driver vs no browser at all) look different to a real
DOM-event collector?

These bots answer that question instead: they drive REAL input (real
mouse-move sequences, real send_keys()/type() calls) against demo-site's own
inline collector (demo-site/utils/session.js + the per-page telemetry
script), and let THAT capture whatever each tool's real automation actually
produces — including navigator.webdriver, which the collector now reads
correctly (see the 2026-07-18 fix to session.js — previously every bot
session reported a clean fingerprint regardless of tool).

Session identity: the collector generates its own sessionId client-side
(crypto.randomUUID(), sessionStorage) — NOT controlled by the bot script.
Each helper here reads that ID back out of the page after driving
interaction, so labeling targets the row the collector actually created.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, release_connection  # noqa: E402

DEMO_SITE_URL = "http://localhost:5173"


def label_session(session_id: str, label: str = "bot") -> bool:
    """Directly label a session row in the DB (bypasses the HTTP/ingest-key
    hop — these bots don't own a Python-side session_id to send it with)."""
    if not session_id:
        return False
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET label = %s WHERE id = %s", (label, session_id))
        conn.commit()
        updated = cursor.rowcount > 0
        cursor.close()
        return updated
    except Exception as e:
        print(f"[label_session] failed for {session_id}: {e}")
        return False
    finally:
        if conn:
            release_connection(conn)


def wait_for_telemetry_flush(seconds: float = 2.5):
    """demo-site's collector sends telemetry on `beforeunload` (navigation
    away) or a 30s interval. Bots trigger it by submitting the login form,
    which the page's own script redirects away from — this just gives the
    keepalive fetch time to land before the driver quits."""
    time.sleep(seconds)


REALISTIC_MOUSE_PATH_STEPS = 14


def curved_path(start, end, jitter=18):
    """A slightly curved path from start (x,y) to end (x,y), broken into
    REALISTIC_MOUSE_PATH_STEPS waypoints — used by every real-interaction
    bot so the underlying *path shape* is comparable across tools; only the
    tool driving the pointer differs."""
    import random
    points = []
    sx, sy = start
    ex, ey = end
    for i in range(1, REALISTIC_MOUSE_PATH_STEPS + 1):
        t = i / REALISTIC_MOUSE_PATH_STEPS
        curve = random.uniform(-jitter, jitter) * (1 - abs(0.5 - t) * 2)
        x = sx + (ex - sx) * t + curve
        y = sy + (ey - sy) * t - curve / 2
        points.append((int(x), int(y)))
    return points
