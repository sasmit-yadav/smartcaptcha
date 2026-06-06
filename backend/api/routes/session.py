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
    insert_session(meta)
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
