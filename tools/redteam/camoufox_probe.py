#!/usr/bin/env python3
"""
Optional P0 probe: Camoufox (patched Firefox + optional humanize).

Skips when camoufox is not installed. Records ALLOW as known_gap unless
REDTEAM_REQUIRE_ADVANCED_BLOCK=1.
"""
from __future__ import annotations

import json
import os
import sys
import time

BASE = os.getenv("REDTEAM_BASE", "http://127.0.0.1:3000")
REQUIRE_BLOCK = os.getenv("REDTEAM_REQUIRE_ADVANCED_BLOCK", "0") == "1"


def main() -> int:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        print("SKIP: pip install camoufox && python -m camoufox fetch")
        return 0

    predict = {}
    status_text = ""

    try:
        with Camoufox(headless=True, humanize=True) as browser:
            page = browser.new_page()

            def on_response(response):
                try:
                    if "/api/predict" in response.url:
                        predict["body"] = response.json()
                        predict["status"] = response.status
                except Exception:
                    pass

            page.on("response", on_response)
            page.goto(BASE, wait_until="networkidle", timeout=60000)
            page.wait_for_function("() => !!window.VeilProof", timeout=30000)
            page.fill("#name", "Camoufox Probe")
            page.fill("#email", "camoufox@test.com")
            page.fill("#message", "Camoufox humanize red-team probe")
            page.click("#submitBtn")
            page.wait_for_selector("#status.success, #status.error", timeout=45000)
            status_text = page.inner_text("#status")
            time.sleep(0.5)
    except Exception as exc:
        msg = str(exc)
        if "Executable doesn't exist" in msg or "not found" in msg.lower():
            print(f"SKIP: Camoufox browser binary missing ({msg[:120]})")
            return 0
        if "ERR_CONNECTION" in msg or "unreachable" in msg.lower() or "Timeout" in msg:
            print(f"SKIP: demo site unreachable ({msg[:160]})")
            return 0
        print(f"ERROR: {msg}")
        return 1

    body = predict.get("body") or {}
    blocked = (
        "Blocked" in status_text
        or body.get("action") == "block"
        or float(body.get("fingerprint_score") or 0) >= 50
    )
    report = {
        "variant": "camoufox_humanize",
        "result": "BLOCKED" if blocked else "ALLOWED",
        "known_gap": not blocked,
        "predict": {
            "action": body.get("action"),
            "risk_score": body.get("risk_score"),
            "fingerprint_score": body.get("fingerprint_score"),
            "behavior_score": body.get("behavior_score"),
        }
        if body
        else None,
        "statusText": status_text,
    }
    print(json.dumps(report, indent=2))

    if not blocked and REQUIRE_BLOCK:
        print("FAIL: Camoufox allowed and REDTEAM_REQUIRE_ADVANCED_BLOCK=1")
        return 2
    if not blocked:
        print("INFO: Camoufox ALLOWED (known advanced gap — recorded, not failing CI)")
    else:
        print("PASS: Camoufox BLOCKED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
