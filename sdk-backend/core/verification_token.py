"""
Verify tokens — the browser/server trust boundary for /api/siteverify.

/api/predict issues a short-lived, single-use, signed token instead of
handing the browser a raw allow/block decision it could ignore or fake. The
customer's *server* redeems that token at /api/siteverify with a secret key,
which is the only way to get a trustworthy decision.

Stateless signed JWT (HS256, python-jose — already a dependency via
core/auth.py). Single-use enforcement lives in core/database.py
(consumed_tokens table), not here. Signed with a subkey derived from
SECRET_KEY plus a `purpose` claim, so /admin/* session JWTs can never be
replayed here (or vice versa) even though both come from the same SECRET_KEY.
"""

import os
import time
import uuid
import hashlib
from typing import Optional

from jose import JWTError, ExpiredSignatureError, jwt

from core.auth import SECRET_KEY

PURPOSE = "siteverify"
ALGORITHM = "HS256"
KID = "v1"
TOKEN_VERSION = 1

VERIFY_TOKEN_TTL_SECONDS = int(os.getenv("VERIFY_TOKEN_TTL_SECONDS", "120"))

# Derived subkey: a leaked/rotated /admin/* signing key never doubles as the
# siteverify signing key, and vice versa.
_SIGNING_KEY = hashlib.sha256(f"{SECRET_KEY}|{PURPOSE}".encode()).hexdigest()


class TokenError(Exception):
    """Raised with a siteverify-style error-code string for siteverify to surface."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def issue_token(
    project_id: str,
    session_id: str,
    risk_score: float,
    action: str,
    hostname: Optional[str],
    site_key_id: str,
) -> str:
    now = int(time.time())
    claims = {
        "purpose": PURPOSE,
        "v": TOKEN_VERSION,
        "jti": uuid.uuid4().hex,
        "project_id": str(project_id),
        "session_id": session_id,
        "risk_score": risk_score,
        "action": action,
        "hostname": hostname,
        "site_key_id": str(site_key_id) if site_key_id else None,
        "iat": now,
        "exp": now + VERIFY_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(claims, _SIGNING_KEY, algorithm=ALGORITHM, headers={"kid": KID})


def decode_token(token: str) -> dict:
    """
    Decode and validate a verify token's signature, expiry, and purpose claim.
    Does NOT check single-use — call core.database.consume_token_jti(jti)
    separately. Raises TokenError with a siteverify-style code on failure.
    """
    if not token:
        raise TokenError("missing-input-response")

    try:
        claims = jwt.decode(token, _SIGNING_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise TokenError("timeout-or-duplicate")
    except JWTError:
        raise TokenError("invalid-input-response")

    if claims.get("purpose") != PURPOSE:
        raise TokenError("invalid-input-response")

    return claims
