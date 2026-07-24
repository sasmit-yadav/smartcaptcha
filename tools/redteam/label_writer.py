"""Shared JSONL writer for P2 red-team labels."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

SCHEMA_VERSION = "veilproof.redteam.v1"
OUT_DIR = Path(__file__).resolve().parent / "out"


def ensure_out() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR


def new_run_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def append_label(
    *,
    stack: str,
    variant: str,
    result: str,
    known_gap: bool,
    base_url: str,
    predict: Optional[dict],
    status_text: str = "",
    run_id: Optional[str] = None,
    attempt: int = 1,
    error: Optional[str] = None,
    notes: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Path:
    """Append one labeled bot session; returns path written."""
    ensure_out()
    path = OUT_DIR / f"{stack}_{day_stamp()}.jsonl"
    body = predict or {}
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "stack": stack,
        "variant": variant,
        "label": "bot",
        "label_source": "redteam_probe",
        "result": result,
        "known_gap": bool(known_gap),
        "base_url": base_url,
        "api_host": os.getenv("VEILPROOF_API", "https://api.veilproof.tech"),
        "predict": {
            "action": body.get("action"),
            "risk_score": body.get("risk_score"),
            "fingerprint_score": body.get("fingerprint_score"),
            "behavior_score": body.get("behavior_score"),
            "network_score": body.get("network_score"),
            "session_id": body.get("session_id") or body.get("sessionId"),
            "automation_signals": body.get("automation_signals"),
            "sdk_version": body.get("sdk_version") or body.get("sdkVersion"),
        }
        if body
        else None,
        "status_text": status_text,
        "run_id": run_id or new_run_id(),
        "attempt": attempt,
    }
    if error:
        record["error"] = error
    if notes:
        record["notes"] = notes
    if extra:
        record.update(extra)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path
