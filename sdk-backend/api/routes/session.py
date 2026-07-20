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
    # Volunteer source (2026-07-20): a session reached via a ?src=volunteer
    # link is a real person by construction (bot scripts never carry this
    # marker — see schemas/telemetry.py), so auto-label 'human'. Honeypot
    # takes priority in the (should-never-happen) case both are somehow true.
    if meta.get('honeypotTriggered'):
        label = 'bot'
    elif meta.get('source') == 'volunteer':
        label = 'human'
    else:
        label = None
    insert_session(meta, label=label)

    tag = ""
    if label == 'bot':
        tag = " [HONEYPOT -> auto-labeled bot]"
    elif label == 'human':
        tag = " [VOLUNTEER -> auto-labeled human]"
    print(f"[SESSION] Session {payload.sessionId} started" + tag)

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
