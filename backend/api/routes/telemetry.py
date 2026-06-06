"""
SmartCaptcha Backend — Telemetry route.
POST /api/telemetry — receives batched events from the SDK.
"""

from fastapi import APIRouter, Request, Header
from typing import Optional
from schemas.telemetry import TelemetryPayload
from core.database import insert_events_batch
import time

router = APIRouter()


@router.post("/api/telemetry")
async def receive_telemetry(
    payload: TelemetryPayload,
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    """
    Receive a batch of telemetry events from the SDK.
    Validates payload, stores events in database.
    """
    # Validate timestamp (not too far in the future) if provided
    now_ms = int(time.time() * 1000)
    payload_ts = getattr(payload, "timestamp", None)
    if payload_ts is not None:
        try:
            if int(payload_ts) > now_ms + 60000:
                return {"queued": False, "error": "Future timestamp rejected"}
        except (ValueError, TypeError):
            return {"queued": False, "error": "Invalid timestamp"}

    # Store events
    events_data = [e.model_dump() for e in payload.events]
    count = insert_events_batch(payload.sessionId, events_data)

    return {
        "queued": True,
        "count": count,
    }
