"""
SmartCaptcha Backend — Session routes.
POST /api/session/start — register a new session.
POST /api/session/end   — close a session with duration.
"""

from fastapi import APIRouter
from typing import Optional
from schemas.telemetry import SessionStartPayload, SessionEndPayload
from core.database import insert_session, update_session_end

router = APIRouter()


@router.post("/api/session/start")
async def session_start(payload: SessionStartPayload):
    """Register a new browsing session."""
    meta = payload.meta.model_dump()
    meta['sessionId'] = payload.sessionId
    # Extract source from meta and map to label
    # The SDK now sends 'source' field in session meta
    # We'll handle this in the database layer by passing it through
    insert_session(meta, label=meta.get('source') if meta.get('source') in ('client', 'demo') else None)
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
