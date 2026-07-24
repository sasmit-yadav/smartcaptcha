"""Unit tests for session-bound request signing (strategy step 3)."""
import base64
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import core.request_signing as request_signing  # noqa: E402
from core.request_signing import (  # noqa: E402
    register_session_key as _register_session_key,
    verify_signature as _verify_signature,
    reset,
)

PROJECT_ID = "project-1"


def register_session_key(session_id, jwk):
    return _register_session_key(PROJECT_ID, session_id, jwk)


def verify_signature(session_id, timestamp, nonce, body, signature):
    return _verify_signature(PROJECT_ID, session_id, timestamp, nonce, body, signature)


def setup_function():
    reset()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _key_material():
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url(numbers.x.to_bytes(32, "big")),
        "y": _b64url(numbers.y.to_bytes(32, "big")),
    }
    return private_key, jwk


def _sign(private_key, session_id: str, timestamp_ms: int, nonce: str, body: bytes) -> str:
    message = f"{session_id}.{timestamp_ms}.{nonce}.".encode() + body
    der = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return (r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex()


def test_register_session_key_is_idempotent():
    _, jwk = _key_material()
    expiry1 = register_session_key("s1", jwk)
    expiry2 = register_session_key("s1", jwk)
    assert expiry2 >= expiry1


def test_different_key_cannot_replace_active_session():
    _, jwk1 = _key_material()
    _, jwk2 = _key_material()
    register_session_key("s1", jwk1)
    try:
        register_session_key("s1", jwk2)
        assert False, "different key must not replace an active session"
    except request_signing.RegistrationError:
        pass


def test_valid_signature_passes():
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b'{"session_duration": 12.5}'
    ts = int(time.time() * 1000)
    nonce = "abc123"
    sig = _sign(private_key, "s1", ts, nonce, body)

    result = verify_signature("s1", str(ts), nonce, body, sig)
    assert result.ok is True
    assert result.unsigned is False


def test_wrong_signature_rejected():
    _, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b'{"session_duration": 12.5}'
    ts = int(time.time() * 1000)
    result = verify_signature("s1", str(ts), "n1", body, "0" * 64)
    assert result.ok is False
    assert "mismatch" in result.reason


def test_tampered_body_rejected():
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    ts = int(time.time() * 1000)
    nonce = "n1"
    sig = _sign(private_key, "s1", ts, nonce, b'{"session_duration": 12.5}')

    # Signature was computed over a different body than what's now verified
    # (e.g. a captured "good" payload spliced onto different feature values).
    result = verify_signature("s1", str(ts), nonce, b'{"session_duration": 999.0}', sig)
    assert result.ok is False


def test_nonce_replay_rejected():
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b"{}"
    ts = int(time.time() * 1000)
    nonce = "reuse-me"
    sig = _sign(private_key, "s1", ts, nonce, body)

    first = verify_signature("s1", str(ts), nonce, body, sig)
    assert first.ok is True

    second = verify_signature("s1", str(ts), nonce, body, sig)
    assert second.ok is False
    assert "replay" in second.reason


def test_signature_cannot_be_spliced_onto_another_session():
    """The core threat this feature targets: capture one good request and
    replay it (even with a fresh nonce/timestamp recomputed) against a
    different session — must fail because that session has its own key.
    """
    _, victim_jwk = _key_material()
    attacker_private, attacker_jwk = _key_material()
    register_session_key("victim-session", victim_jwk)
    register_session_key("attacker-session", attacker_jwk)
    body = b'{"session_duration": 12.5}'
    ts = int(time.time() * 1000)
    nonce = "n1"
    # Attacker can only sign with their own session's private key...
    sig = _sign(attacker_private, "attacker-session", ts, nonce, body)

    # ...and tries to present it as a request for the victim's session.
    result = verify_signature("victim-session", str(ts), nonce, body, sig)
    assert result.ok is False


def test_registered_key_is_bound_to_project():
    private_key, jwk = _key_material()
    _register_session_key("project-a", "s1", jwk)
    body = b"{}"
    timestamp = int(time.time() * 1000)
    signature = _sign(private_key, "s1", timestamp, "n1", body)
    result = _verify_signature(
        "project-b", "s1", str(timestamp), "n1", body, signature
    )
    assert result.ok is False
    assert "no active session key" in result.reason


def test_stale_timestamp_rejected(monkeypatch):
    monkeypatch.setattr(request_signing, "MAX_CLOCK_SKEW_SECONDS", 60)
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b"{}"
    stale_ts = int((time.time() - 3600) * 1000)  # 1 hour old
    nonce = "n1"
    sig = _sign(private_key, "s1", stale_ts, nonce, body)

    result = verify_signature("s1", str(stale_ts), nonce, body, sig)
    assert result.ok is False
    assert "window" in result.reason


def test_unknown_session_rejected():
    body = b"{}"
    ts = int(time.time() * 1000)
    result = verify_signature("never-started", str(ts), "n1", body, "a" * 64)
    assert result.ok is False
    assert "register" in result.reason


def test_expired_key_rejected(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(request_signing, "SESSION_KEY_TTL_SECONDS", 1)
    monkeypatch.setattr(request_signing.time, "time", lambda: clock[0])
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    clock[0] += 1.1
    body = b"{}"
    ts = int(clock[0] * 1000)
    sig = _sign(private_key, "s1", ts, "n1", body)

    result = verify_signature("s1", str(ts), "n1", body, sig)
    assert result.ok is False
    assert "expired" in result.reason


def test_nonces_are_retained_for_entire_freshness_window(monkeypatch):
    """Regression: the old 64-entry set evicted arbitrary live nonces."""
    monkeypatch.setattr(request_signing, "_MAX_NONCES_PER_SESSION", 128)
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b"{}"
    timestamp = int(time.time() * 1000)
    first_nonce = "nonce-0"
    first_signature = _sign(private_key, "s1", timestamp, first_nonce, body)

    for i in range(70):
        nonce = f"nonce-{i}"
        signature = _sign(private_key, "s1", timestamp, nonce, body)
        assert verify_signature("s1", str(timestamp), nonce, body, signature).ok

    replay = verify_signature("s1", str(timestamp), first_nonce, body, first_signature)
    assert replay.ok is False
    assert "replay" in replay.reason


def test_future_dated_nonce_retained_until_its_timestamp_expires(monkeypatch):
    """A +skew timestamp remains valid for roughly 2*skew after acceptance."""
    clock = [1000.0]
    monkeypatch.setattr(request_signing, "MAX_CLOCK_SKEW_SECONDS", 120)
    monkeypatch.setattr(request_signing.time, "time", lambda: clock[0])
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    body = b"{}"
    timestamp = int((clock[0] + 120) * 1000)
    nonce = "future-nonce"
    signature = _sign(private_key, "s1", timestamp, nonce, body)
    assert verify_signature("s1", str(timestamp), nonce, body, signature).ok

    clock[0] += 121  # request timestamp is still inside the +/-120s window
    replay = verify_signature("s1", str(timestamp), nonce, body, signature)
    assert replay.ok is False
    assert "replay" in replay.reason


def test_same_key_renewal_preserves_live_nonce_history(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(request_signing, "SESSION_KEY_TTL_SECONDS", 10)
    monkeypatch.setattr(request_signing.time, "time", lambda: clock[0])
    private_key, jwk = _key_material()
    register_session_key("s1", jwk)
    clock[0] += 9
    body = b"{}"
    timestamp = int((clock[0] + 120) * 1000)
    signature = _sign(private_key, "s1", timestamp, "n1", body)
    assert verify_signature("s1", str(timestamp), "n1", body, signature).ok

    clock[0] += 2  # original key registration expired
    register_session_key("s1", jwk)
    replay = verify_signature("s1", str(timestamp), "n1", body, signature)
    assert replay.ok is False
    assert "replay" in replay.reason


def test_session_store_enforces_hard_bound(monkeypatch):
    monkeypatch.setattr(request_signing, "_MAX_SESSIONS", 2)
    for session_id in ("s1", "s2", "s3"):
        _, jwk = _key_material()
        register_session_key(session_id, jwk)
    assert len(request_signing._sessions) == 2
    assert (PROJECT_ID, "s1") not in request_signing._sessions


def test_unsigned_request_soft_mode_passes_through(monkeypatch):
    monkeypatch.setattr(request_signing, "REQUEST_SIGNING_MODE", "soft")
    result = verify_signature("s1", None, None, b"{}", None)
    assert result.ok is True
    assert result.unsigned is True


def test_unsigned_request_strict_mode_rejected(monkeypatch):
    monkeypatch.setattr(request_signing, "REQUEST_SIGNING_MODE", "strict")
    result = verify_signature("s1", None, None, b"{}", None)
    assert result.ok is False
    assert result.unsigned is False
    assert result.error_code == "signing_required"


def test_default_mode_is_strict():
    assert request_signing.REQUEST_SIGNING_MODE == "strict"


def test_partial_headers_rejected_in_soft_mode(monkeypatch):
    monkeypatch.setattr(request_signing, "REQUEST_SIGNING_MODE", "soft")
    result = _verify_signature(
        PROJECT_ID, "s1", "1710000000000", None, b"{}", None
    )
    assert result.ok is False
    assert result.error_code == "signing_incomplete"


def test_disabled_accepts_everything(monkeypatch):
    monkeypatch.setattr(request_signing, "REQUEST_SIGNING_DISABLED", True)
    result = _verify_signature(None, None, None, None, b"garbage", None)
    assert result.ok is True
    assert result.unsigned is True
