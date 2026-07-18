"""
VeilProof API — Session lifecycle routes.
POST /api/session/start — register a new browsing session.
POST /api/session/end   — close a session with duration.
"""

from fastapi import APIRouter, Depends

from schemas.telemetry import SessionStartPayload, SessionEndPayload
from core.database import insert_session, update_session_end
from core.ingest_auth import verify_ingest_source

router = APIRouter(dependencies=[Depends(verify_ingest_source)])


@router.post("/api/session/start")
async def session_start(payload: SessionStartPayload):
    """Register a new browsing session."""
    meta = payload.meta.model_dump()
    meta['sessionId'] = payload.sessionId

    # Honeypot (strategy step 7): a filled hidden field is a near-certain bot,
    # so auto-label the session 'bot' — a free, high-confidence training label
    # that needs no human review. Only ever ASSIGNS 'bot'; never clears a label.
    label = 'bot' if meta.get('honeypotTriggered') else None
    insert_session(meta, label=label)

    print(f"[SESSION] Session {payload.sessionId} started"
          + (" [HONEYPOT -> auto-labeled bot]" if label else ""))

    return {
        "sessionId": payload.sessionId,
        "accepted": True,
    }


@router.post("/api/session/end")
async def session_end(payload: SessionEndPayload):
    """Close a session and record its duration."""
    duration_ms = payload.duration or 0
    update_session_end(payload.sessionId, duration_ms)
    return {
        "sessionId": payload.sessionId,
        "processed": True,
    }
