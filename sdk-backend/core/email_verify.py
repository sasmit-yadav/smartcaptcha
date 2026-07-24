"""Email-verification tokens (SHA-256 hashed, single-use, 48-hour TTL)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from core.database import DATABASE_URL

VERIFY_TOKEN_TTL_HOURS = 48
TOKEN_BYTES = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_verify_token(
    user_id: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(raw)
    expires = _utcnow() + timedelta(hours=VERIFY_TOKEN_TTL_HOURS)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_email_verify_tokens
                SET used_at = NOW()
                WHERE user_id = %s::uuid AND used_at IS NULL
                """,
                (str(user_id),),
            )
            cursor.execute(
                """
                INSERT INTO auth_email_verify_tokens
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


def consume_verify_token(raw_token: str) -> dict:
    raw = (raw_token or "").strip()
    if not raw or len(raw) > 200:
        raise ValueError("Invalid or expired verification link")

    token_hash = _hash_token(raw)
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT t.id AS token_id, t.user_id, t.expires_at, t.used_at,
                       u.email, u.full_name, u.is_admin, u.is_active,
                       u.email_verified_at,
                       COALESCE(u.has_password, TRUE) AS has_password,
                       COALESCE(u.google_linked, FALSE) AS google_linked
                FROM auth_email_verify_tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token_hash = %s
                FOR UPDATE OF t
                """,
                (token_hash,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Invalid or expired verification link")
            if row.get("used_at") is not None:
                raise ValueError("Invalid or expired verification link")
            if not row.get("is_active", True):
                raise ValueError("Invalid or expired verification link")

            expires = row["expires_at"]
            if expires is not None:
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < _utcnow():
                    raise ValueError("Invalid or expired verification link")

            if row.get("email_verified_at") is not None:
                cursor.execute(
                    "UPDATE auth_email_verify_tokens SET used_at = NOW() WHERE id = %s::uuid",
                    (str(row["token_id"]),),
                )
                conn.commit()
                return {
                    "id": row["user_id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "is_admin": row["is_admin"],
                    "has_password": row["has_password"],
                    "google_linked": row["google_linked"],
                    "email_verified_at": row["email_verified_at"],
                    "already_verified": True,
                }

            cursor.execute(
                """
                UPDATE users
                SET email_verified_at = NOW()
                WHERE id = %s::uuid
                RETURNING id, email, full_name, company_name, is_admin,
                          COALESCE(has_password, TRUE) AS has_password,
                          COALESCE(google_linked, FALSE) AS google_linked,
                          email_verified_at
                """,
                (str(row["user_id"]),),
            )
            updated = dict(cursor.fetchone())
            cursor.execute(
                "UPDATE auth_email_verify_tokens SET used_at = NOW() WHERE id = %s::uuid",
                (str(row["token_id"]),),
            )
            cursor.execute(
                """
                UPDATE auth_email_verify_tokens
                SET used_at = NOW()
                WHERE user_id = %s::uuid AND used_at IS NULL
                """,
                (str(row["user_id"]),),
            )
            conn.commit()
            updated["already_verified"] = False
            return updated
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise ValueError("Unable to verify email. Please try again.")
    finally:
        conn.close()


def mark_email_verified(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET email_verified_at = COALESCE(email_verified_at, NOW())
                WHERE id = %s::uuid
                """,
                (str(user_id),),
            )
            conn.commit()
    finally:
        conn.close()


def is_email_verified(user: dict) -> bool:
    return user.get("email_verified_at") is not None
