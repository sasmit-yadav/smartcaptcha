#!/usr/bin/env python3
"""
P2.1 batch collector — run N Camoufox (+ optional rebrowser) probes and
write a summary JSON next to JSONL labels.

Usage (demo must be up on REDTEAM_BASE):
  set REDTEAM_BASE=http://127.0.0.1:3000
  set REDTEAM_RUNS=10
  python tools/redteam/collect_p2.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
REPO = ROOT.parent.parent


def run(cmd: list[str], env: dict) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(REPO), env=env)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = os.getenv("REDTEAM_RUNS", "5")
    env = os.environ.copy()
    env["REDTEAM_RUNS"] = runs
    env.setdefault("REDTEAM_BASE", "http://127.0.0.1:3000")

    codes = {}
    codes["camoufox"] = run([sys.executable, str(ROOT / "camoufox_probe.py")], env)

    if env.get("REDTEAM_SKIP_REBROWSER") != "1":
        codes["rebrowser"] = run(["node", str(ROOT / "rebrowser_probe.mjs")], env)
    else:
        codes["rebrowser"] = None

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    summary = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "redteam_runs_env": runs,
        "base": env.get("REDTEAM_BASE"),
        "exit_codes": codes,
        "jsonl_hint": str(OUT / f"camoufox_{day}.jsonl"),
        "target": "N>=50 Camoufox labeled bots before P2.2 ingest",
    }
    path = OUT / f"summary_{day}.json"
    # append-friendly: overwrite latest summary for the day
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if codes.get("camoufox") in (0, 2) else codes.get("camoufox", 1)


if __name__ == "__main__":
    sys.exit(main())
