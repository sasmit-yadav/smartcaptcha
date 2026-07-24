#!/usr/bin/env python3
"""
P0 red-team: unsigned /api/predict forge must be rejected in strict mode.

Industry equivalent of "unsigned webhook payloads must 401" (Stripe/GitHub).
Exit 0 = forge correctly rejected. Exit 2 = forge accepted (regression).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.getenv("VEILPROOF_API", "https://api.veilproof.tech").rstrip("/")
SITE_KEY = os.getenv("VEILPROOF_SITE_KEY", "").strip()


def main() -> int:
    if not SITE_KEY:
        print("SKIP: set VEILPROOF_SITE_KEY to run live unsigned forge probe")
        return 0

    body = {
        "sdkVersion": "1.1.10",
        "sessionId": "redteam-unsigned-forge",
        "event_count": 80,
        "session_duration": 25.0,
        "webdriver_flag": False,
        "automation_score": 0,
        "automation_signals": [],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0",
        "platform": "Win32",
        "has_touch": False,
        # Human-ish filler so a soft-mode backend wouldn't block on behavior alone.
        "avg_mouse_vel": 120.0,
        "mouse_curvature_std": 0.8,
        "mouse_jerk_std": 5000.0,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    req = urllib.request.Request(
        f"{API}/api/predict",
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": SITE_KEY,
            "Origin": "http://127.0.0.1:3000",
            "User-Agent": body["user_agent"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode()
            print("FAIL: unsigned forge was ACCEPTED")
            print(payload[:500])
            return 2
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")
        print(f"HTTP {err.code}: {detail[:400]}")
        if err.code == 401:
            # Prefer structured error_code when present.
            try:
                parsed = json.loads(detail)
                code = (parsed.get("detail") or {}).get("error_code") if isinstance(parsed.get("detail"), dict) else None
                if code and code != "signing_required":
                    print(f"WARN: expected signing_required, got {code}")
            except json.JSONDecodeError:
                pass
            print("PASS: unsigned forge rejected (strict signing)")
            return 0
        print(f"FAIL: unexpected status {err.code} (want 401 signing_required)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
