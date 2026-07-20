"""
D.1 read: how does the CURRENTLY-DEPLOYED V5 model (no retraining) score the
browser-use LLM-agent persona's real sessions, served through the actual
live /api/predict path (same methodology as verify_serving.py — RiskEngine
threshold, calibrated model, anomaly + network axes, not an offline OOF
estimate)?
"""
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, release_connection  # noqa: E402
from features.feature_columns import FEATURE_COLUMNS  # noqa: E402

BACKEND = "http://localhost:8001"
API_KEY = "demo-key"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

AGENTIC_SESSION_IDS = [
    "8c177d86-b8d3-49c0-86e9-e43ac40f534e",  # Gemini, interactive test
    "176000c8-faaa-495a-a8ff-637122fd0db0",  # Gemini, batch
    "5cf78721-f937-4c5a-af35-3bd6e71183c9",  # Gemini, batch
    "fb355d25-aa67-452a-a9f9-5eb8db7820c2",  # Gemini, batch
    "7fb9af11-25c8-471f-9474-5b64ee418b57",  # Gemini, batch
    "459e9b06-c7bf-4247-890e-4cff1ec1ade2",  # OpenRouter (nemotron-nano-12b-v2-vl:free)
]


def fetch_rows():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cols = ["session_id", *FEATURE_COLUMNS, "label", "webdriver_flag"]
        placeholders = ", ".join(["%s"] * len(AGENTIC_SESSION_IDS))
        cur.execute(
            f"SELECT {', '.join(cols)} FROM session_features WHERE session_id::text IN ({placeholders})",
            AGENTIC_SESSION_IDS,
        )
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]
        cur.close()
        return [dict(zip(colnames, r)) for r in rows]
    finally:
        release_connection(conn)


def predict(row):
    body = {c: (float(row[c]) if row[c] is not None else 0.0) for c in FEATURE_COLUMNS}
    body["webdriver_flag"] = bool(row.get("webdriver_flag", False))
    body["user_agent"] = BROWSER_UA
    body["has_touch"] = False
    body["platform"] = "Win32"
    body["sessionId"] = str(row["session_id"])
    r = requests.post(
        f"{BACKEND}/api/predict",
        json=body,
        headers={"X-API-Key": API_KEY, "User-Agent": BROWSER_UA},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def main():
    rows = fetch_rows()
    print(f"Found {len(rows)}/{len(AGENTIC_SESSION_IDS)} agentic sessions with computed features\n")
    blocked = 0
    for row in rows:
        try:
            res = predict(row)
        except Exception as e:
            print(f"{str(row['session_id'])[:8]}...  predict failed: {e}")
            continue
        verdict = "BLOCK" if res["action"] == "block" else "allow"
        if res["action"] == "block":
            blocked += 1
        print(
            f"{str(row['session_id'])[:8]}...  {verdict:6s}  "
            f"risk={res['risk_score']:>5.1f}  behavior={res['behavior_score']:>5.1f}  "
            f"fingerprint={res['fingerprint_score']:>5.1f}  confidence={res['confidence']:.2f}"
        )
    n = len(rows)
    if n:
        print(f"\nAgentic-bot detection rate: {blocked}/{n} blocked = {blocked/n:.1%}")
        print("(n is small — this is a preliminary read, not a generalization estimate; see docs/current_task.md)")


if __name__ == "__main__":
    main()
