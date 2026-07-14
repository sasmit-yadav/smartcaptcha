"""
Ingestion source verification for telemetry/session endpoints.

Browsers can't keep secrets, so ingestion is gated two ways:
- Origin allowlist (ALLOWED_ORIGINS env, comma-separated, e.g.
  "https://demo.smartcaptcha.ai,https://smartcaptcha.vercel.app").
  Set to "*" to explicitly disable the check (dev only).
- Optional shared key (INGEST_API_KEY env) sent via X-Ingest-Key header,
  for server-side clients like the ml-train bot scripts.
"""

import os
from typing import Optional

from fastapi import Header, HTTPException

DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def get_allowed_origins() -> list:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if not origins:
        print(
            "[INGEST AUTH] ALLOWED_ORIGINS not set — falling back to localhost "
            "dev origins only. Set it in production."
        )
        return DEV_ORIGINS
    return origins


async def verify_ingest_source(
    origin: Optional[str] = Header(None),
    x_ingest_key: Optional[str] = Header(None),
):
    """FastAPI dependency: reject ingestion requests from unknown origins."""
    ingest_key = os.getenv("INGEST_API_KEY")
    if ingest_key and x_ingest_key == ingest_key:
        return

    allowed = get_allowed_origins()
    if "*" in allowed:
        return
    if origin and origin.rstrip("/") in allowed:
        return

    raise HTTPException(
        status_code=403,
        detail="Origin not allowed for telemetry ingestion",
    )
