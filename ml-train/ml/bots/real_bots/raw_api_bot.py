"""
Tool-config bot #4: raw scripted API client — no browser at all.

Stands in for the strategy doc's "curl-impersonate" category: a script that
talks to the API directly (requests library) with no browser, no DOM, and
therefore no mouse/keyboard/scroll telemetry to speak of. This is the
cheapest, dumbest real-world bot — credential stuffing, scraping,
API-abuse scripts — and should be the easiest case for the model precisely
because there's nothing resembling human behaviour to accidentally get
half-right. Unlike the browser-driven tool-config bots, this one owns its
own session_id (there's no page-side collector to defer to).
"""
import os
import sys
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))
load_dotenv(ROOT / ".env")

try:
    from .common import label_session
except ImportError:
    from common import label_session  # noqa: E402

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "")


def run():
    """POST a session with zero-to-minimal synthetic telemetry directly to
    the API, no browser involved. Returns the session_id, or None on
    failure."""
    session_id = str(uuid.uuid4())
    headers = {"X-Ingest-Key": INGEST_API_KEY}

    try:
        requests.post(
            f"{BACKEND_URL}/api/session/start",
            json={
                "sessionId": session_id,
                "meta": {
                    "sessionId": session_id,
                    "userAgent": "python-requests/2.31.0",
                    "deviceType": "desktop",
                    "screenWidth": 1920,
                    "screenHeight": 1080,
                    "platform": "Linux",
                    "webdriverFlag": False,  # no browser at all; nothing to flag
                },
            },
            headers=headers,
            timeout=5,
        )

        # A real scraper submits the form fields in one shot with no
        # interaction preamble — one click event, no mouse/keyboard events.
        requests.post(
            f"{BACKEND_URL}/api/telemetry",
            json={
                "sessionId": session_id,
                "meta": {"sessionId": session_id},
                "events": [
                    {"type": "cl", "t": int(time.time() * 1000), "x": 0, "y": 0, "target": "submit-button"}
                ],
                "timestamp": int(time.time() * 1000),
            },
            headers=headers,
            timeout=5,
        )

        time.sleep(0.2)
        requests.post(
            f"{BACKEND_URL}/api/session/end",
            json={"sessionId": session_id, "duration": 50},
            headers=headers,
            timeout=5,
        )
    except Exception as e:
        print(f"[raw_api_bot] error: {e}")
        return None

    label_session(session_id, "bot")
    print(f"[raw_api_bot] labeled session {session_id[:8]}...")
    return session_id


if __name__ == "__main__":
    run()
