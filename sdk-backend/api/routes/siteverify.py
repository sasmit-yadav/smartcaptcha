"""
VeilProof API — Server-side verification route.
POST /api/siteverify — the customer's *server* redeems a verify token
(issued by /api/predict) with a secret key. This is the actual trust
boundary: the browser response from /api/predict is not one, since a bot
can ignore or fake it.

reCAPTCHA-compatible: accepts JSON ({"token": "..."} + a key header) or
classic form-encoded (`secret=...&response=...`), and failures are returned
as HTTP 200 with `{"success": false, "error-codes": [...]}` rather than a
4xx, matching the reCAPTCHA siteverify convention customers already expect.
"""

import logging

from fastapi import APIRouter, Request, Header, Depends

from api_key_manager import APIKeyManager
from core.verification_token import decode_token, TokenError
from core.database import consume_token_jti, maybe_prune_consumed_tokens
from core.rate_limit import rate_limit

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def _error(*codes: str) -> dict:
    return {"success": False, "error-codes": list(codes)}


@router.post("/api/siteverify", dependencies=[Depends(rate_limit("siteverify_ip", limit=240, window_seconds=60))])
async def siteverify(
    request: Request,
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    Redeem a verify token issued by /api/predict. Returns the risk decision
    if the token is valid, unexpired, unused, and bound to the same project
    as the secret key presented here.
    """
    content_type = request.headers.get("content-type", "")
    secret = x_api_key
    if not secret and authorization and authorization.startswith("Bearer "):
        secret = authorization[7:]
    token = None

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        secret = form.get("secret") or secret
        token = form.get("response")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        secret = body.get("secret") or secret
        token = body.get("token") or body.get("response")

    maybe_prune_consumed_tokens()

    if not secret:
        return _error("missing-input-secret")

    key_info = APIKeyManager.verify_api_key(secret)
    if not key_info:
        return _error("invalid-input-secret")
    if key_info.get("key_type") != "secret":
        return _error("invalid-input-secret")

    if not token:
        return _error("missing-input-response")

    try:
        claims = decode_token(token)
    except TokenError as e:
        return _error(e.code)

    if str(claims.get("project_id")) != str(key_info["project_id"]):
        return _error("invalid-input-response")

    if not consume_token_jti(claims["jti"]):
        return _error("timeout-or-duplicate")

    return {
        "success": True,
        "risk_score": claims.get("risk_score"),
        "action": claims.get("action"),
        "hostname": claims.get("hostname"),
        "session_id": claims.get("session_id"),
        "challenge_ts": claims.get("iat"),
    }
