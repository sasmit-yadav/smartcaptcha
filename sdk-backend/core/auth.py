"""
Session token issuance/verification for /admin/* routes.

Replaces the old model of trusting a client-supplied `user-id` header (anyone
who knew or guessed a UUID could act as that user). Login/register/
google-login issue a signed JWT; every authenticated /admin/* route now
requires a valid Bearer token instead.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. It signs /admin/* session "
        "tokens and must be a long random secret (e.g. `openssl rand -hex 32`), "
        "set in your local .env or the Render dashboard. Never hardcode it."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(user_id: str, email: str, is_admin: bool = False) -> str:
    """Issue a signed session token for a logged-in user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "is_admin": bool(is_admin), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


class CurrentUser:
    __slots__ = ("user_id", "email", "is_admin")

    def __init__(self, user_id: str, email: str, is_admin: bool):
        self.user_id = user_id
        self.email = email
        self.is_admin = is_admin


def get_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """FastAPI dependency: require and decode a valid Bearer session token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return CurrentUser(user_id=user_id, email=payload.get("email", ""), is_admin=payload.get("is_admin", False))


def get_current_super_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """FastAPI dependency: require a valid token AND super-admin privileges."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    return user
