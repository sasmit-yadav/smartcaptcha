import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-production-use-32b")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/veilproof_test")
os.environ.pop("RESEND_API_KEY", None)

from core import email as email_mod  # noqa: E402


def test_email_disabled_without_api_key():
    assert email_mod.email_enabled() is False
    assert email_mod.send_welcome_email("a@b.com", full_name="Ada") is False


def test_welcome_templates_render():
    wrapped = email_mod._wrap_html("t", "<p>x</p>")
    assert "VeilProof" in wrapped
    assert "veilproof-logo.png" in wrapped
    name = email_mod._display_name("Ada Lovelace", "ada@example.com")
    assert name == "Ada"
    assert email_mod._display_name(None, "builder@example.com") == "builder"
    assert email_mod._greeting_name("Ada Lovelace", "ada@example.com") == "Ada Lovelace"


def test_password_changed_noop_without_key():
    assert (
        email_mod.send_password_changed_email(
            "a@b.com",
            full_name="Ada",
            ip="1.2.3.4",
            user_agent="Mozilla/5.0",
            was_set=False,
        )
        is False
    )
