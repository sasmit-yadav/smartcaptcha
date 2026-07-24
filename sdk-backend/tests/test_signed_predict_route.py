"""Route-level contract test for register -> signed /api/predict."""
import base64
import json
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost/unused")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-that-is-at-least-32-bytes")

from api.routes import predict as predict_route  # noqa: E402
from core import database, request_signing  # noqa: E402


def _key_material():
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    return private_key, {
        "kty": "EC",
        "crv": "P-256",
        "x": encode(numbers.x.to_bytes(32, "big")),
        "y": encode(numbers.y.to_bytes(32, "big")),
    }


def _sign(private_key, session_id, timestamp, nonce, body):
    message = f"{session_id}.{timestamp}.{nonce}.".encode() + body
    der = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return (r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex()


class FakeDetector:
    def predict_session(self, *_args, **_kwargs):
        return {
            "action": "allow",
            "risk_score": 10.0,
            "behavior_score": 10.0,
            "fingerprint_score": 0.0,
            "confidence": 0.8,
        }


def _key_info():
    return {
        "key_id": "site-key-id",
        "project_id": "project-id",
        "project_name": "Project",
        "key_type": "site",
        "allowed_domains": ["*"],
    }


def _client(monkeypatch):
    request_signing.reset()
    monkeypatch.setattr(predict_route, "verify_key_or_demo", lambda _key: _key_info())
    monkeypatch.setattr(predict_route, "enforce", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(predict_route, "get_detector", lambda: FakeDetector())
    monkeypatch.setattr(database, "insert_session_prediction", lambda **_kwargs: None)
    monkeypatch.setattr(predict_route.APIKeyManager, "update_last_used", lambda *_args: None)
    monkeypatch.setattr(predict_route, "issue_token", lambda **_kwargs: "verify-token")
    app = FastAPI()
    app.include_router(predict_route.router)
    return TestClient(app)


def test_registered_browser_key_signs_predict_body(monkeypatch):
    client = _client(monkeypatch)
    private_key, public_jwk = _key_material()
    session_id = "13c9cf53-0880-459b-a47a-e36d705621c5"

    registered = client.post(
        "/api/signing/register",
        headers={"X-API-Key": "vp_site_test"},
        json={"sessionId": session_id, "publicKey": public_jwk},
    )
    assert registered.status_code == 200
    assert registered.json()["registered"] is True

    body = {
        "sdkVersion": "1.1.3",
        "sessionId": session_id,
        "session_duration": 12.5,
        "event_count": 20,
        "user_agent": "Mozilla/5.0",
        "platform": "Win32",
    }
    raw_body = json.dumps(body, separators=(",", ":")).encode()
    timestamp = int(time.time() * 1000)
    nonce = "0123456789abcdef0123456789abcdef"
    signature = _sign(private_key, session_id, timestamp, nonce, raw_body)

    response = client.post(
        "/api/predict",
        headers={
            "X-API-Key": "vp_site_test",
            "Content-Type": "application/json",
            "X-VeilProof-Timestamp": str(timestamp),
            "X-VeilProof-Nonce": nonce,
            "X-VeilProof-Signature": signature,
        },
        content=raw_body,
    )
    assert response.status_code == 200
    assert response.json()["verification_token"] == "verify-token"


def test_signed_predict_requires_session_id_in_body(monkeypatch):
    client = _client(monkeypatch)
    private_key, public_jwk = _key_material()
    session_id = "13c9cf53-0880-459b-a47a-e36d705621c5"
    request_signing.register_session_key("project-id", session_id, public_jwk)

    raw_body = b'{"sdkVersion":"1.1.3","event_count":20}'
    timestamp = int(time.time() * 1000)
    nonce = "0123456789abcdef0123456789abcdef"
    signature = _sign(private_key, session_id, timestamp, nonce, raw_body)
    response = client.post(
        "/api/predict",
        headers={
            "X-API-Key": "vp_site_test",
            "Content-Type": "application/json",
            "X-VeilProof-Timestamp": str(timestamp),
            "X-VeilProof-Nonce": nonce,
            "X-VeilProof-Signature": signature,
        },
        content=raw_body,
    )
    assert response.status_code == 401
    assert "missing session id" in response.json()["detail"]


def test_signing_rollout_counters_track_signed_and_unsigned(monkeypatch):
    client = _client(monkeypatch)
    private_key, public_jwk = _key_material()
    session_id = "13c9cf53-0880-459b-a47a-e36d705621c5"

    client.post(
        "/api/signing/register",
        headers={"X-API-Key": "vp_site_test"},
        json={"sessionId": session_id, "publicKey": public_jwk},
    )

    unsigned = client.post(
        "/api/predict",
        headers={"X-API-Key": "vp_site_test", "Content-Type": "application/json"},
        content=b'{"sdkVersion":"1.1.2","sessionId":"legacy","event_count":1}',
    )
    assert unsigned.status_code == 200

    body = {
        "sdkVersion": "1.1.3",
        "sessionId": session_id,
        "event_count": 20,
        "user_agent": "Mozilla/5.0",
        "platform": "Win32",
    }
    raw_body = json.dumps(body, separators=(",", ":")).encode()
    timestamp = int(time.time() * 1000)
    nonce = "fedcba9876543210fedcba9876543210"
    signature = _sign(private_key, session_id, timestamp, nonce, raw_body)
    signed = client.post(
        "/api/predict",
        headers={
            "X-API-Key": "vp_site_test",
            "Content-Type": "application/json",
            "X-VeilProof-Timestamp": str(timestamp),
            "X-VeilProof-Nonce": nonce,
            "X-VeilProof-Signature": signature,
        },
        content=raw_body,
    )
    assert signed.status_code == 200

    stats = request_signing.get_signing_stats()
    assert stats["register_ok"] == 1
    assert stats["predict_unsigned"] == 1
    assert stats["predict_signed"] == 1
    assert stats["unsigned_share"] == 0.5
    assert stats["mode"] == "soft"
