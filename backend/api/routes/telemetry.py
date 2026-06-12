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
    # Store events — use Python field names so DB columns map reliably
    events_data = [e.model_dump(by_alias=False) for e in payload.events]
    count = insert_events_batch(payload.sessionId, events_data)

    return {
        "queued": True,
        "count": count,
    }
