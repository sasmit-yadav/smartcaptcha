#!/usr/bin/env python3
"""
Optional P2 probe: Camoufox (patched Firefox + optional humanize).

Writes labeled JSONL under tools/redteam/out/ (schema: SCHEMA.md).
Skips when camoufox is not installed. Records ALLOW as known_gap unless
REDTEAM_REQUIRE_ADVANCED_BLOCK=1.

Env:
  REDTEAM_BASE          demo URL (default http://127.0.0.1:3000)
  REDTEAM_RUNS          number of sessions (default 1)
  REDTEAM_REQUIRE_ADVANCED_BLOCK=1  fail process if any ALLOW
  REDTEAM_HEADLESS=0    headed
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from label_writer import append_label, new_run_id  # noqa: E402

BASE = os.getenv("REDTEAM_BASE", "http://127.0.0.1:3000")
REQUIRE_BLOCK = os.getenv("REDTEAM_REQUIRE_ADVANCED_BLOCK", "0") == "1"
RUNS = max(1, int(os.getenv("REDTEAM_RUNS", "1")))
HEADLESS = os.getenv("REDTEAM_HEADLESS", "1") != "0"


def _one_run(attempt: int, run_id: str) -> dict:
    from camoufox.sync_api import Camoufox

    predict: dict = {}
    status_text = ""
    error = None
    result = "ERROR"

    try:
        with Camoufox(headless=HEADLESS, humanize=True) as browser:
            page = browser.new_page()

            def on_response(response):
                try:
                    if "/api/predict" in response.url:
                        predict["body"] = response.json()
                        predict["status"] = response.status
                except Exception:
                    pass

            page.on("response", on_response)
            page.goto(BASE, wait_until="networkidle", timeout=90000)
            page.wait_for_function("() => !!window.VeilProof", timeout=45000)
            page.fill("#name", f"Camoufox Probe {attempt}")
            page.fill("#email", f"camoufox{attempt}@test.com")
            page.fill("#message", "Camoufox humanize red-team probe P2")
            page.click("#submitBtn")
            page.wait_for_selector("#status.success, #status.error", timeout=60000)
            status_text = page.inner_text("#status")
            try:
                sid = page.evaluate("() => sessionStorage.getItem('sc_session_id')")
                if sid:
                    predict["session_id"] = sid
            except Exception:
                pass
            body_preview = predict.get("body") or {}
            if body_preview.get("session_id") and not predict.get("session_id"):
                predict["session_id"] = body_preview.get("session_id")
            time.sleep(0.4)
    except Exception as exc:
        error = str(exc)
        msg = error.lower()
        if "executable doesn't exist" in msg or "not found" in msg:
            result = "SKIP"
        elif "err_connection" in msg or "unreachable" in msg or "timeout" in msg:
            result = "SKIP"
        else:
            result = "ERROR"

    body = predict.get("body") or {}
    if result not in ("SKIP", "ERROR") or body:
        blocked = (
            "Blocked" in status_text
            or body.get("action") == "block"
            or float(body.get("fingerprint_score") or 0) >= 50
            or float(body.get("risk_score") or 0) >= 50
        )
        if body or status_text:
            result = "BLOCKED" if blocked else "ALLOWED"

    session_id = predict.get("session_id") or body.get("session_id")
    if session_id and isinstance(body, dict):
        body = {**body, "session_id": session_id}

    path = append_label(
        stack="camoufox",
        variant="camoufox_humanize",
        result=result,
        known_gap=(result == "ALLOWED"),
        base_url=BASE,
        predict=body if body else None,
        status_text=status_text,
        run_id=run_id,
        attempt=attempt,
        error=error,
        notes="P2.1 labeled advanced stealth",
        extra={"fingerprint_axis_gap": float((body or {}).get("fingerprint_score") or 0) == 0},
    )
    return {
        "attempt": attempt,
        "result": result,
        "known_gap": result == "ALLOWED",
        "predict": body or None,
        "status_text": status_text,
        "error": error,
        "jsonl": str(path),
    }


def main() -> int:
    try:
        from camoufox.sync_api import Camoufox  # noqa: F401
    except ImportError:
        print("SKIP: pip install camoufox && python -m camoufox fetch")
        return 0

    run_id = new_run_id()
    reports = []
    any_allow = False
    hard_fail = False

    for i in range(1, RUNS + 1):
        print(f"[camoufox] attempt {i}/{RUNS} -> {BASE}", flush=True)
        try:
            rep = _one_run(i, run_id)
        except Exception as exc:
            rep = {
                "attempt": i,
                "result": "ERROR",
                "known_gap": False,
                "error": str(exc),
            }
            append_label(
                stack="camoufox",
                variant="camoufox_humanize",
                result="ERROR",
                known_gap=False,
                base_url=BASE,
                predict=None,
                run_id=run_id,
                attempt=i,
                error=str(exc),
            )
            hard_fail = True
        reports.append(rep)
        print(json.dumps(rep, indent=2))
        if rep.get("result") == "ALLOWED":
            any_allow = True
        if rep.get("result") == "ERROR" and not str(rep.get("error") or "").lower().startswith(
            ("executable", "skip")
        ):
            # soft: connection skips already marked SKIP
            pass

    summary = {
        "run_id": run_id,
        "stack": "camoufox",
        "runs": RUNS,
        "blocked": sum(1 for r in reports if r.get("result") == "BLOCKED"),
        "allowed": sum(1 for r in reports if r.get("result") == "ALLOWED"),
        "skip": sum(1 for r in reports if r.get("result") == "SKIP"),
        "error": sum(1 for r in reports if r.get("result") == "ERROR"),
    }
    print("SUMMARY", json.dumps(summary))

    if any_allow and REQUIRE_BLOCK:
        print("FAIL: Camoufox allowed and REDTEAM_REQUIRE_ADVANCED_BLOCK=1")
        return 2
    if any_allow:
        print("INFO: Camoufox ALLOWED (known advanced gap — labeled for P2 training)")
    elif summary["blocked"]:
        print("PASS: Camoufox BLOCKED")
    return 1 if hard_fail and summary["blocked"] + summary["allowed"] == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
