"""
Session token issuance/verification for /admin/* routes.

Industry-oriented model (OWASP ASVS session guidance, adapted for SPA):
  - Short-lived access JWT (Bearer) for API calls
  - Longer-lived refresh token (opaque, stored hashed) with rotation
  - iss/aud/typ pinned; alg allow-list HS256 only
  - Logout / refresh revoke server-side refresh rows

Replaces the old model of trusting a client-supplied `user-id` header.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. It signs /admin/* session "
        "tokens and must be a long random secret (e.g. `openssl rand -hex 32`), "
        "set in your local .env or the hosting dashboard. Never hardcode it."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "veilproof-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "veilproof-dashboard")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, email: str, is_admin: bool = False) -> str:
    """Issue a short-lived signed access JWT."""
    now = _utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": bool(is_admin),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "typ": "access",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(
    user_id: str,
    *,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[str, datetime]:
    """Create opaque refresh token, store SHA-256 hash, return (raw, expires_at)."""
    from core.database import get_connection, release_connection
    from psycopg2.extras import RealDictCursor

    raw = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw)
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO auth_refresh_tokens (user_id, token_hash, expires_at, user_agent, ip)
                VALUES (%s::uuid, %s, %s, %s, %s)
                """,
                (str(user_id), token_hash, expires_at.replace(tzinfo=None), (user_agent or "")[:500], ip),
            )
            conn.commit()
    finally:
        release_connection(conn)

    return raw, expires_at


def revoke_refresh_token(raw: str) -> None:
    """Mark a refresh token revoked (logout / rotation of previous)."""
    if not raw:
        return
    from core.database import get_connection, release_connection

    token_hash = _hash_refresh_token(raw)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_refresh_tokens
                SET revoked_at = NOW()
                WHERE token_hash = %s AND revoked_at IS NULL
                """,
                (token_hash,),
            )
            conn.commit()
    finally:
        release_connection(conn)


def revoke_all_refresh_tokens(user_id: str) -> None:
    from core.database import get_connection, release_connection

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_refresh_tokens
                SET revoked_at = NOW()
                WHERE user_id = %s::uuid AND revoked_at IS NULL
                """,
                (str(user_id),),
            )
            conn.commit()
    finally:
        release_connection(conn)


def rotate_refresh_token(
    raw: str,
    *,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[dict, str, str]:
    """
    Validate refresh token, revoke it, issue new access + refresh.
    Returns (user_row_dict, access_token, new_refresh_token).
    """
    from core.database import get_connection, release_connection
    from psycopg2.extras import RealDictCursor

    if not raw:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    token_hash = _hash_refresh_token(raw)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT t.id, t.user_id, t.expires_at, t.revoked_at,
                       u.email, u.is_admin, u.is_active
                FROM auth_refresh_tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token_hash = %s
                """,
                (token_hash,),
            )
            data = cursor.fetchone()
            if not data:
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

            if data.get("revoked_at") is not None:
                # Possible theft: revoke all sessions for this user.
                cursor.execute(
                    """
                    UPDATE auth_refresh_tokens SET revoked_at = NOW()
                    WHERE user_id = %s AND revoked_at IS NULL
                    """,
                    (data["user_id"],),
                )
                conn.commit()
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

            expires_at = data["expires_at"]
            if getattr(expires_at, "tzinfo", None) is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < _utcnow() or not data.get("is_active", True):
                cursor.execute(
                    "UPDATE auth_refresh_tokens SET revoked_at = NOW() WHERE id = %s",
                    (data["id"],),
                )
                conn.commit()
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

            cursor.execute(
                "UPDATE auth_refresh_tokens SET revoked_at = NOW() WHERE id = %s",
                (data["id"],),
            )
            conn.commit()
            user_id = str(data["user_id"])
            email = data["email"]
            is_admin = bool(data.get("is_admin"))
    finally:
        release_connection(conn)

    user = {"id": user_id, "email": email, "is_admin": is_admin}
    access = create_access_token(user["id"], user["email"], user["is_admin"])
    new_refresh, _ = issue_refresh_token(user["id"], user_agent=user_agent, ip=ip)
    return user, access, new_refresh


def issue_session_tokens(
    user_id: str,
    email: str,
    is_admin: bool = False,
    *,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> dict:
    """Standard login/register/google response token bundle."""
    access = create_access_token(user_id, email, is_admin)
    refresh, refresh_exp = issue_refresh_token(user_id, user_agent=user_agent, ip=ip)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_at": int(refresh_exp.timestamp()),
    }


class CurrentUser:
    __slots__ = ("user_id", "email", "is_admin")

    def __init__(self, user_id: str, email: str, is_admin: bool):
        self.user_id = user_id
        self.email = email
        self.is_admin = is_admin


def get_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """FastAPI dependency: require and decode a valid Bearer access token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer ") :]
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    if payload.get("typ") not in (None, "access"):
        # Reject refresh tokens used as Bearer access.
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return CurrentUser(
        user_id=user_id,
        email=payload.get("email", ""),
        is_admin=bool(payload.get("is_admin", False)),
    )


def get_current_super_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """FastAPI dependency: require a valid token AND super-admin privileges."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    return user
