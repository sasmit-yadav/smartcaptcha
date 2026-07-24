"""Password-reset tokens (SHA-256 hashed, single-use, 60-minute TTL)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

from core.database import DATABASE_URL
from core.password_policy import validate_password

RESET_TOKEN_TTL_MINUTES = 60
TOKEN_BYTES = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_reset_token(
    user_id: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Invalidate prior unused tokens for the user and return a new raw token."""
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(raw)
    expires = _utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_password_reset_tokens
                SET used_at = NOW()
                WHERE user_id = %s::uuid AND used_at IS NULL
                """,
                (str(user_id),),
            )
            cursor.execute(
                """
                INSERT INTO auth_password_reset_tokens
                    (user_id, token_hash, expires_at, ip, user_agent)
                VALUES (%s::uuid, %s, %s, %s, %s)
                """,
                (str(user_id), token_hash, expires.replace(tzinfo=None), ip, user_agent),
            )
            conn.commit()
        return raw
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def consume_reset_token(raw_token: str, new_password: str) -> dict:
    """
    Validate token, set password, mark token used.
    Returns updated user row. Raises ValueError on failure.
    """
    raw = (raw_token or "").strip()
    if not raw or len(raw) > 200:
        raise ValueError("Invalid or expired reset link")

    token_hash = _hash_token(raw)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT t.id AS token_id, t.user_id, t.expires_at, t.used_at,
                       u.email, u.full_name, u.is_admin,
                       COALESCE(u.has_password, TRUE) AS has_password,
                       COALESCE(u.google_linked, FALSE) AS google_linked,
                       u.is_active
                FROM auth_password_reset_tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token_hash = %s
                FOR UPDATE OF t
                """,
                (token_hash,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Invalid or expired reset link")
            if row.get("used_at") is not None:
                raise ValueError("Invalid or expired reset link")
            if not row.get("is_active", True):
                raise ValueError("Invalid or expired reset link")

            expires = row["expires_at"]
            if expires is not None:
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < _utcnow():
                    raise ValueError("Invalid or expired reset link")

            email = row["email"]
            pw_ok, pw_err = validate_password(new_password, email=email)
            if not pw_ok:
                raise ValueError(pw_err or "Invalid password")

            new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()
            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s, has_password = TRUE
                WHERE id = %s::uuid
                RETURNING id, email, full_name, company_name, is_admin,
                          TRUE AS has_password,
                          COALESCE(google_linked, FALSE) AS google_linked,
                          email_verified_at
                """,
                (new_hash, str(row["user_id"])),
            )
            updated = dict(cursor.fetchone())
            cursor.execute(
                """
                UPDATE auth_password_reset_tokens
                SET used_at = NOW()
                WHERE id = %s::uuid
                """,
                (str(row["token_id"]),),
            )
            cursor.execute(
                """
                UPDATE auth_password_reset_tokens
                SET used_at = NOW()
                WHERE user_id = %s::uuid AND used_at IS NULL
                """,
                (str(row["user_id"]),),
            )
            conn.commit()
            return updated
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise ValueError("Unable to reset password. Please try again.")
    finally:
        conn.close()
