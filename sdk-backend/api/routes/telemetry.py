"""
VeilProof API — Telemetry route.
POST /api/telemetry — receives batched behavioral events from the SDK and
the demo site, and stores them for model training and analytics.
"""

import json

from fastapi import APIRouter, Request, Depends

from schemas.telemetry import TelemetryPayload
from core.database import insert_events_batch
from core.ingest_auth import verify_ingest_source

router = APIRouter(dependencies=[Depends(verify_ingest_source)])


@router.post("/api/telemetry")
async def receive_telemetry(request: Request):
    """
    Receive a batch of telemetry events.
    Validates payload, stores events in database.
    """
    body = None
    try:
        body = await request.body()
        payload_dict = json.loads(body.decode('utf-8'))

        payload = TelemetryPayload(**payload_dict)

        # Store events — use Python field names so DB columns map reliably
        events_data = [e.model_dump(by_alias=False) for e in payload.events]
        count = insert_events_batch(payload.sessionId, events_data)

        print(f"[TELEMETRY] Session {payload.sessionId}: {count} events stored")

        return {
            "queued": True,
            "count": count,
        }
    except Exception as e:
        print(f"[TELEMETRY ERROR] {str(e)}")
        print(f"[TELEMETRY ERROR] Body: {body[:500] if body else 'empty'}")
        raise
