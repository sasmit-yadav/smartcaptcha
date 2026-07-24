"""
Request signing — session-bound ECDSA for /api/predict (strategy step 3:
"Harden the SDK: sign + nonce + timestamp the payload... stop replay of a
known-good vector").

The site key is public by design, and a symmetric secret delivered by the
server to browser JavaScript is not a real secret. The SDK therefore creates
a non-exportable ECDSA P-256 private key locally and registers only its public
key. /api/predict requires an ECDSA signature over the exact raw request body,
session id, timestamp and nonce. A captured request cannot be modified or
replayed without the original tab's private CryptoKey.

What this stops: an attacker who has captured one real, human-looking
request cannot replay it verbatim (nonce is single-use), cannot replay it
after it goes stale (timestamp window), and cannot splice a captured "good"
request onto a *different* registered session (the signature is bound to one
session's public key and won't verify under another sessionId). What this
does NOT stop: an attacker who controls a real, current browser session
end-to-end, or can register its own session key, can still submit whatever
feature values it wants for that session. No client-side signing scheme can
make client-computed features trustworthy. Cross-session feature reuse is
handled separately by core/replay_detection.py. This layer is deliberately
limited to request integrity and exact-request replay protection.

Soft-enforced by default (REQUEST_SIGNING_MODE=soft): requests with none of
the signing headers at all (older SDK versions already deployed via CDN/npm,
or environments without Web Crypto) are
let through unsigned, same as before this feature existed. A request that
DOES send signing headers but fails verification is always rejected
regardless of mode — a bad signature is a tamper/forgery signal, not a
legacy-client signal. Set REQUEST_SIGNING_MODE=strict once a signing-capable
SDK version is the deployed baseline, to reject unsigned requests outright.
REQUEST_SIGNING_DISABLED=1 is a full kill-switch (accepts everything).

In-memory, single-instance store — same caveat as core/rate_limit.py and
core/replay_detection.py: no Redis, so this only enforces correctly on one
backend instance. Fine for the current single-Heroku-dyno deployment.
"""
from __future__ import annotations

import base64
import hashlib
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

REQUEST_SIGNING_DISABLED = os.getenv("REQUEST_SIGNING_DISABLED", "0") == "1"
REQUEST_SIGNING_MODE = os.getenv("REQUEST_SIGNING_MODE", "soft")  # "soft" | "strict"

SESSION_KEY_TTL_SECONDS = int(os.getenv("SESSION_KEY_TTL_SECONDS", str(30 * 60)))
MAX_CLOCK_SKEW_SECONDS = int(os.getenv("REQUEST_SIGNING_MAX_SKEW_SECONDS", "120"))
_MAX_SESSIONS = int(os.getenv("REQUEST_SIGNING_MAX_SESSIONS", "50000"))
_MAX_NONCES_PER_SESSION = int(os.getenv("REQUEST_SIGNING_MAX_NONCES_PER_SESSION", "512"))

_lock = threading.Lock()
# In insertion order so the oldest state can be evicted when the hard bound
# is reached. This is a real bound, not merely an expired-entry sweep.
_sessions: OrderedDict = OrderedDict()

# Soft-rollout observability: process-local counters (reset on dyno restart).
# Exposed via /api/stats so unsigned share can be monitored before enabling
# REQUEST_SIGNING_MODE=strict. Reasons are truncated to keep the map bounded.
_stats = {
    "predict_signed": 0,
    "predict_unsigned": 0,
    "predict_rejected": 0,
    "register_ok": 0,
    "register_conflict": 0,
}
_reject_reasons: dict = {}
_MAX_REASON_KEYS = 32


@dataclass
class SignatureResult:
    ok: bool
    reason: Optional[str] = None
    # True only when the request carried no signing headers at all (legacy
    # client / disableTelemetry) — distinguishes "nothing to verify" from an
    # active verification failure, for callers that want to log differently.
    unsigned: bool = False


class RegistrationError(ValueError):
    """Invalid or conflicting public-key registration."""


@dataclass
class SessionKeyState:
    public_key: ec.EllipticCurvePublicKey
    fingerprint: str
    issued_at: float
    # nonce -> request-valid-until epoch seconds. Entries remain until that
    # particular request timestamp can no longer pass the skew check (future
    # timestamps stay valid longer than acceptance_time + skew).
    spent_nonces: OrderedDict


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _public_key_from_jwk(jwk: dict) -> tuple[ec.EllipticCurvePublicKey, str]:
    if not isinstance(jwk, dict):
        raise RegistrationError("publicKey must be a JWK object")
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise RegistrationError("only EC P-256 public keys are supported")
    try:
        x_bytes = _b64url_decode(jwk["x"])
        y_bytes = _b64url_decode(jwk["y"])
        if len(x_bytes) != 32 or len(y_bytes) != 32:
            raise ValueError
        numbers = ec.EllipticCurvePublicNumbers(
            int.from_bytes(x_bytes, "big"),
            int.from_bytes(y_bytes, "big"),
            ec.SECP256R1(),
        )
        public_key = numbers.public_key()
    except (KeyError, TypeError, ValueError) as exc:
        raise RegistrationError("malformed EC public key") from exc
    fingerprint = hashlib.sha256(x_bytes + y_bytes).hexdigest()
    return public_key, fingerprint


def _sweep_expired_locked(now: float) -> None:
    expired = [
        sid for sid, state in _sessions.items()
        if now - state.issued_at > SESSION_KEY_TTL_SECONDS
    ]
    for sid in expired:
        _sessions.pop(sid, None)


def register_session_key(project_id: str, session_id: str, public_jwk: dict) -> int:
    """Register a browser-generated public key for one session.

    Re-registering the same key is idempotent. A different key cannot replace
    an active session key; that prevents anyone who learns a session id from
    hijacking it. Once expired, the SDK may register a fresh key. Returns the
    expiry timestamp in milliseconds.
    """
    if not project_id:
        raise RegistrationError("missing project id")
    if not session_id or len(session_id) > 100:
        raise RegistrationError("invalid session id")
    state_key = (str(project_id), session_id)
    public_key, fingerprint = _public_key_from_jwk(public_jwk)
    now = time.time()
    with _lock:
        existing = _sessions.get(state_key)
        if existing is not None:
            if existing.fingerprint == fingerprint:
                # Renewal keeps still-live nonce history, so a request accepted
                # just before key expiry cannot become replayable after the
                # same browser refreshes its registration.
                existing.issued_at = now
                _sessions.move_to_end(state_key)
                return int((now + SESSION_KEY_TTL_SECONDS) * 1000)
            if now - existing.issued_at <= SESSION_KEY_TTL_SECONDS:
                raise RegistrationError("a different key is already registered for this session")
            _sessions.pop(state_key, None)

        _sweep_expired_locked(now)
        while len(_sessions) >= _MAX_SESSIONS:
            _sessions.popitem(last=False)
        _sessions[state_key] = SessionKeyState(
            public_key=public_key,
            fingerprint=fingerprint,
            issued_at=now,
            spent_nonces=OrderedDict(),
        )
        return int((now + SESSION_KEY_TTL_SECONDS) * 1000)


def verify_signature(project_id: Optional[str], session_id: Optional[str],
                      timestamp_header: Optional[str],
                      nonce: Optional[str], raw_body: bytes,
                      signature_hex: Optional[str]) -> SignatureResult:
    """Verify an /api/predict request's ECDSA signature, freshness, and nonce.

    `raw_body` must be the exact bytes received on the wire (not a
    re-serialized reconstruction) — signing the literal transmitted bytes,
    the same approach webhook signature schemes (Stripe, GitHub, Slack) use,
    avoids any cross-language JSON float/ordering serialization mismatch
    that a "recompute canonical JSON and sign that" scheme would risk.
    """
    if REQUEST_SIGNING_DISABLED:
        return SignatureResult(ok=True, unsigned=True)

    if not (timestamp_header and nonce and signature_hex):
        if REQUEST_SIGNING_MODE == "strict":
            return SignatureResult(ok=False, reason="request signing required")
        return SignatureResult(ok=True, unsigned=True)

    if not session_id:
        return SignatureResult(ok=False, reason="missing session id")
    if not project_id:
        return SignatureResult(ok=False, reason="missing project id")
    state_key = (str(project_id), session_id)

    try:
        timestamp_ms = int(timestamp_header)
    except (TypeError, ValueError):
        return SignatureResult(ok=False, reason="malformed timestamp")

    now = time.time()
    if abs(now - timestamp_ms / 1000.0) > MAX_CLOCK_SKEW_SECONDS:
        return SignatureResult(ok=False, reason="timestamp outside allowed window")

    with _lock:
        state = _sessions.get(state_key)
        if state is None:
            return SignatureResult(
                ok=False, reason="no active session key (register the public key first)"
            )
        if now - state.issued_at > SESSION_KEY_TTL_SECONDS:
            return SignatureResult(ok=False, reason="session key expired")

        expired_nonces = [
            spent_nonce for spent_nonce, valid_until in state.spent_nonces.items()
            if valid_until < now
        ]
        for spent_nonce in expired_nonces:
            state.spent_nonces.pop(spent_nonce, None)
        if nonce in state.spent_nonces:
            return SignatureResult(ok=False, reason="nonce already used (replay)")
        if len(state.spent_nonces) >= _MAX_NONCES_PER_SESSION:
            return SignatureResult(ok=False, reason="too many signed requests in freshness window")

        try:
            raw_signature = bytes.fromhex(signature_hex)
            if len(raw_signature) != 64:
                raise ValueError
            r = int.from_bytes(raw_signature[:32], "big")
            s = int.from_bytes(raw_signature[32:], "big")
            der_signature = encode_dss_signature(r, s)
            message = f"{session_id}.{timestamp_ms}.{nonce}.".encode() + raw_body
            state.public_key.verify(
                der_signature,
                message,
                ec.ECDSA(hashes.SHA256()),
            )
        except (InvalidSignature, TypeError, ValueError):
            return SignatureResult(ok=False, reason="signature mismatch")

        state.spent_nonces[nonce] = (
            timestamp_ms / 1000.0 + MAX_CLOCK_SKEW_SECONDS
        )

    return SignatureResult(ok=True)


def record_predict_outcome(result: SignatureResult) -> None:
    """Update soft-rollout counters after a /api/predict signature check."""
    with _lock:
        if not result.ok:
            _stats["predict_rejected"] += 1
            reason = (result.reason or "unknown")[:120]
            if reason not in _reject_reasons and len(_reject_reasons) >= _MAX_REASON_KEYS:
                reason = "other"
            _reject_reasons[reason] = _reject_reasons.get(reason, 0) + 1
        elif result.unsigned:
            _stats["predict_unsigned"] += 1
        else:
            _stats["predict_signed"] += 1


def record_register_outcome(*, ok: bool, conflict: bool = False) -> None:
    """Update counters after a /api/signing/register attempt."""
    with _lock:
        if ok:
            _stats["register_ok"] += 1
        elif conflict:
            _stats["register_conflict"] += 1


def get_signing_stats() -> dict:
    """Snapshot for /api/stats — safe to expose (no secrets, no session ids)."""
    with _lock:
        signed = _stats["predict_signed"]
        unsigned = _stats["predict_unsigned"]
        rejected = _stats["predict_rejected"]
        decided = signed + unsigned
        return {
            "mode": "disabled" if REQUEST_SIGNING_DISABLED else REQUEST_SIGNING_MODE,
            "predict_signed": signed,
            "predict_unsigned": unsigned,
            "predict_rejected": rejected,
            "unsigned_share": (
                round(unsigned / decided, 4) if decided else None
            ),
            "reject_reasons": dict(_reject_reasons),
            "register_ok": _stats["register_ok"],
            "register_conflict": _stats["register_conflict"],
            "active_sessions": len(_sessions),
        }


def reset() -> None:
    """Clear all in-memory state — for tests."""
    with _lock:
        _sessions.clear()
        _stats.update(
            predict_signed=0,
            predict_unsigned=0,
            predict_rejected=0,
            register_ok=0,
            register_conflict=0,
        )
        _reject_reasons.clear()
