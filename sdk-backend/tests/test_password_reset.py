import os
import sys
from pathlib import Path
from unittest import mock

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-production-use-32b")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/veilproof_test")
os.environ.pop("RESEND_API_KEY", None)

from core import email as email_mod  # noqa: E402
from core.password_reset import _hash_token  # noqa: E402


def test_reset_and_verify_email_templates_render():
    assert email_mod.send_password_reset_email(
        "a@b.com",
        reset_url="https://veilproof.tech/reset-password?token=abc",
        full_name="Ada",
    ) is False
    assert email_mod.send_password_reset_google_only_email("a@b.com", full_name="Ada") is False
    assert email_mod.send_email_verification_email(
        "a@b.com",
        verify_url="https://veilproof.tech/verify-email?token=abc",
        full_name="Ada",
    ) is False


def test_token_hash_is_sha256_hex():
    h = _hash_token("test-token")
    assert len(h) == 64
    assert h == _hash_token("test-token")
    assert h != _hash_token("other")


def test_forgot_password_always_ok(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app

    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")
    client = TestClient(app)
    r = client.post("/admin/forgot-password", json={"email": "nobody-exists-xyz@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "account exists" in body.get("message", "").lower() or "sent" in body.get("message", "").lower()


def test_reset_password_rejects_bad_token(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app

    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")
    client = TestClient(app)
    r = client.post(
        "/admin/reset-password",
        json={"token": "this-is-not-a-valid-reset-token-value", "new_password": "A-strong-password-99"},
    )
    assert r.status_code == 400
