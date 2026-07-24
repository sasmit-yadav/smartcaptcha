#!/usr/bin/env python3
"""
P2.2 — ingest red-team JSONL labels into Postgres `sessions.label='bot'`.

Requires DATABASE_URL (same DB as production/sdk-backend).

Usage:
  set DATABASE_URL=postgres://...
  python tools/redteam/ingest_p2.py
  python tools/redteam/ingest_p2.py --file tools/redteam/out/camoufox_20260724.jsonl

After ingest, run feature extraction + retrain from ml-train (P2.3).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "sdk-backend"
sys.path.insert(0, str(BACKEND))

OUT = Path(__file__).resolve().parent / "out"


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def label_session(session_id: str, label: str = "bot") -> bool:
    from core.database import get_connection, release_connection

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET label = %s WHERE id = %s", (label, session_id))
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        return ok
    finally:
        if conn:
            release_connection(conn)


def main() -> int:
    if not os.getenv("DATABASE_URL"):
        print("FAIL: set DATABASE_URL to the VeilProof Postgres URL")
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=None, help="Single JSONL file")
    ap.add_argument("--stack", default="camoufox", help="Stack prefix when scanning out/")
    args = ap.parse_args()

    files = [args.file] if args.file else sorted(OUT.glob(f"{args.stack}_*.jsonl"))
    if not files:
        print(f"No JSONL files found under {OUT}")
        return 1

    stats = {"rows": 0, "with_session": 0, "labeled": 0, "missing_row": 0}
    for path in files:
        if path is None or not path.exists():
            continue
        print(f"Ingest {path}")
        for rec in iter_jsonl(path):
            stats["rows"] += 1
            pred = rec.get("predict") or {}
            sid = pred.get("session_id") or rec.get("session_id")
            if not sid:
                continue
            stats["with_session"] += 1
            if label_session(str(sid), "bot"):
                stats["labeled"] += 1
            else:
                stats["missing_row"] += 1

    print(json.dumps(stats, indent=2))
    if stats["with_session"] == 0:
        print(
            "INFO: no session_id in JSONL yet — re-run probes after API echoes "
            "session_id (deployed) and SDK flush; see SCHEMA.md"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
