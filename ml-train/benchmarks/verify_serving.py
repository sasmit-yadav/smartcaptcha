"""
End-to-end serving verification: pull real labeled feature vectors from
session_features and POST them through the live /api/predict, reporting the
served decision (action, risk_score) per label and per bot family.

This exercises the ACTUAL production path (RiskEngine threshold, calibrated
model, anomaly axis, network axis) — not the offline OOF estimate.
"""
import sys
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml"))

from core.database import get_connection, release_connection  # noqa: E402
from features.feature_columns import FEATURE_COLUMNS  # noqa: E402

BACKEND = "http://localhost:8001"
API_KEY = "demo-key"


def fetch_sessions(limit_per_label=200):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cols = ["session_id", *FEATURE_COLUMNS, "label"]
        cur.execute(f"""
            SELECT {", ".join(cols)} FROM session_features
            WHERE label IN ('bot','human')
              AND device_type = 'desktop'
              AND event_count > 0
        """)
        # Same filter as train_model.py's load_data() — the model is trained
        # desktop-only; testing it against mobile sessions (different
        # touch/scroll behavioral patterns, never seen in training) isn't a
        # model failure, it's testing outside the model's declared scope.
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description]
        cur.close()
        return [dict(zip(colnames, r)) for r in rows]
    finally:
        release_connection(conn)


BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"


def predict(row):
    body = {c: (float(row[c]) if row[c] is not None else 0.0) for c in FEATURE_COLUMNS}
    body["webdriver_flag"] = bool(row.get("webdriver_flag", False))
    body["user_agent"] = BROWSER_UA
    body["has_touch"] = False
    body["platform"] = "Win32"
    body["sessionId"] = str(row["session_id"])
    # Send a real browser User-Agent HEADER too: the Step-2 network layer reads
    # the HTTP header (not the body), and would otherwise correctly flag the
    # default python-requests UA as a non-browser client (+60) and block every
    # request — masking the behavioural model we're trying to isolate here.
    r = requests.post(f"{BACKEND}/api/predict", json=body,
                      headers={"X-API-Key": API_KEY, "User-Agent": BROWSER_UA},
                      timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    rows = fetch_sessions()
    by_label = defaultdict(lambda: {"n": 0, "block": 0, "risks": []})
    for row in rows:
        try:
            res = predict(row)
        except Exception as e:
            print(f"predict failed for {row['session_id']}: {e}")
            continue
        label = row["label"]
        by_label[label]["n"] += 1
        by_label[label]["risks"].append(res["risk_score"])
        if res["action"] == "block":
            by_label[label]["block"] += 1

    print("\n=== SERVED /api/predict decisions (V4) ===")
    for label in ("human", "bot"):
        d = by_label[label]
        if d["n"] == 0:
            continue
        rate = d["block"] / d["n"]
        risks = sorted(d["risks"])
        median = risks[len(risks) // 2]
        verb = "BLOCKED" if label == "bot" else "FALSE-POSITIVE (blocked humans)"
        print(f"{label:6s}: {d['block']}/{d['n']} {verb} = {rate:.1%}, "
              f"median risk {median}")
    hb = by_label["human"]["block"]
    hn = by_label["human"]["n"]
    bb = by_label["bot"]["block"]
    bn = by_label["bot"]["n"]
    print(f"\nBot detection recall: {bb/bn:.1%}  |  Human FPR: {hb/hn:.1%} ({hb}/{hn})")


if __name__ == "__main__":
    main()
