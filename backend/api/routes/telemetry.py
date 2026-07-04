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
    request: Request,
):
    """
    Receive a batch of telemetry events from the SDK.
    Validates payload, stores events in database.
    """
    try:
        import json
        body = await request.body()
        body_str = body.decode('utf-8')
        payload_dict = json.loads(body_str)
        
        payload = TelemetryPayload(**payload_dict)
        
        # Store events — use Python field names so DB columns map reliably
        events_data = [e.model_dump(by_alias=False) for e in payload.events]
        count = insert_events_batch(payload.sessionId, events_data)

        event_types = [e.type for e in payload.events]
        print(f"[TELEMETRY] Session {payload.sessionId}: {count} events stored")
        print(f"[TELEMETRY] Event types: {event_types}")

        return {
            "queued": True,
            "count": count,
        }
    except Exception as e:
        print(f"[TELEMETRY ERROR] {str(e)}")
        print(f"[TELEMETRY ERROR] Body: {body[:500] if body else 'empty'}")
        raise
