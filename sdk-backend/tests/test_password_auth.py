"""Password policy + auth token shape tests (no DB required for policy)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# auth.py requires SECRET_KEY at import time
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-production-use-32b")

from core.password_policy import validate_email, validate_password, normalize_email  # noqa: E402
from core import auth as auth_mod  # noqa: E402


def test_email_normalization():
    assert normalize_email("  Foo@Example.COM ") == "foo@example.com"
    ok, err = validate_email("not-an-email")
    assert not ok and err


def test_password_too_short():
    ok, err = validate_password("shortpass")
    assert not ok
    assert "12" in (err or "")


def test_password_common_rejected():
    ok, err = validate_password("password1234")
    assert not ok


def test_password_rejects_email_local():
    ok, err = validate_password("sasmit1234567", email="sasmit@example.com")
    assert not ok


def test_password_accepts_strong():
    ok, err = validate_password("correct-horse-battery-9")
    assert ok, err


def test_access_token_has_iss_aud_typ():
    token = auth_mod.create_access_token("user-1", "a@b.com", False)
    from jose import jwt

    payload = jwt.decode(
        token,
        auth_mod.SECRET_KEY,
        algorithms=[auth_mod.ALGORITHM],
        audience=auth_mod.JWT_AUDIENCE,
        issuer=auth_mod.JWT_ISSUER,
    )
    assert payload["typ"] == "access"
    assert payload["email"] == "a@b.com"
    assert payload["sub"] == "user-1"
