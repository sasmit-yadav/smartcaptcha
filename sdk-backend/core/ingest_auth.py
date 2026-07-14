"""
Ingestion source verification for telemetry/session endpoints.

A request may store telemetry if ANY of these pass, checked in order:
1. A valid customer API key in X-API-Key (the SDK sends this on every call).
2. The shared INGEST_API_KEY env value in X-Ingest-Key (server-side clients
   like the ml-train bot scripts).
3. The request Origin is in the ALLOWED_ORIGINS allowlist (the demo site
   sends no real API key, so it is admitted by origin).

ALLOWED_ORIGINS: comma-separated, e.g.
  "https://ecologicalhubdemo.vercel.app,https://demo.smartcaptcha.ai"
Set to "*" to explicitly disable the origin check (dev only).
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
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """FastAPI dependency: reject ingestion requests from unknown sources."""
    # 1. Valid customer API key (SDK integrations on arbitrary domains)
    if x_api_key:
        try:
            from api_key_manager import APIKeyManager
            if APIKeyManager.verify_api_key(x_api_key):
                return
        except Exception as e:
            # Fall through to the other checks; never 500 on a lookup error
            print(f"[INGEST AUTH] API key lookup failed: {e}")

    # 2. Shared server-side ingest key
    ingest_key = os.getenv("INGEST_API_KEY")
    if ingest_key and x_ingest_key == ingest_key:
        return

    # 3. Origin allowlist (demo site / first-party pages)
    allowed = get_allowed_origins()
    if "*" in allowed:
        return
    if origin and origin.rstrip("/") in allowed:
        return

    raise HTTPException(
        status_code=403,
        detail="Origin not allowed for telemetry ingestion",
    )
