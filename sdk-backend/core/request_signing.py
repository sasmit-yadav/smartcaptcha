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

Modes (industry rollout pattern — Stripe/Cloudflare-style webhook signing):
  - strict (DEFAULT): unsigned /api/predict is rejected. Production ready
    once unsigned_share ≈ 0 (already observed on api.veilproof.tech).
  - soft: unsigned allowed for emergency rollback / legacy CDN clients.
    Incomplete signing headers (any present, not all) are ALWAYS rejected —
    that is a tamper signal, never a legacy-client signal.
  - REQUEST_SIGNING_DISABLED=1: full kill-switch (accepts everything).

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
# Production default is strict. Soft remains an explicit rollback lever.
_raw_mode = (os.getenv("REQUEST_SIGNING_MODE") or "strict").strip().lower()
REQUEST_SIGNING_MODE = _raw_mode if _raw_mode in ("soft", "strict") else "strict"

SESSION_KEY_TTL_SECONDS = int(os.getenv("SESSION_KEY_TTL_SECONDS", str(30 * 60)))
MAX_CLOCK_SKEW_SECONDS = int(os.getenv("REQUEST_SIGNING_MAX_SKEW_SECONDS", "120"))
_MAX_SESSIONS = int(os.getenv("REQUEST_SIGNING_MAX_SESSIONS", "50000"))
_MAX_NONCES_PER_SESSION = int(os.getenv("REQUEST_SIGNING_MAX_NONCES_PER_SESSION", "512"))
# Soft-mode readiness gate for ops dashboards (not auto-flipped).
UNSIGNED_SHARE_STRICT_READY = float(os.getenv("REQUEST_SIGNING_UNSIGNED_READY", "0.01"))
MIN_SAMPLES_STRICT_READY = int(os.getenv("REQUEST_SIGNING_MIN_SAMPLES_READY", "50"))
# Persist keys/nonces to Postgres so strict signing survives multi-dyno.
# memory = unit tests / emergency; auto = postgres outside pytest.
_STORE_MODE = (os.getenv("REQUEST_SIGNING_STORE") or "auto").strip().lower()


def _persist_enabled() -> bool:
    if _STORE_MODE in ("memory", "off", "0"):
        return False
    if _STORE_MODE == "postgres":
        return True
    # auto
    return "PYTEST_CURRENT_TEST" not in os.environ


def _db():
    """Lazy import so unit tests can run without a live DB pool."""
    from core import database
    return database

_lock = threading.Lock()
# In insertion order so the oldest state can be evicted when the hard bound
# is reached. This is a real bound, not merely an expired-entry sweep.
_sessions: OrderedDict = OrderedDict()

# Observability: process-local counters (reset on dyno restart).
_stats = {
    "predict_signed": 0,
    "predict_unsigned": 0,
    "predict_rejected": 0,
    "register_ok": 0,
    "register_conflict": 0,
}
_reject_reasons: dict = {}
_MAX_REASON_KEYS = 32

# Machine-stable error codes (API clients / dashboards). Reasons stay human.
ERROR_SIGNING_REQUIRED = "signing_required"
ERROR_SIGNING_INCOMPLETE = "signing_incomplete"
ERROR_MISSING_SESSION = "missing_session_id"
ERROR_MISSING_PROJECT = "missing_project_id"
ERROR_BAD_TIMESTAMP = "malformed_timestamp"
ERROR_TIMESTAMP_SKEW = "timestamp_skew"
ERROR_NO_SESSION_KEY = "no_session_key"
ERROR_KEY_EXPIRED = "session_key_expired"
ERROR_NONCE_REPLAY = "nonce_replay"
ERROR_NONCE_FLOOD = "nonce_flood"
ERROR_SIGNATURE_MISMATCH = "signature_mismatch"


@dataclass
class SignatureResult:
    ok: bool
    reason: Optional[str] = None
    # True only when the request carried no signing headers at all (legacy
    # client / disableTelemetry) — distinguishes "nothing to verify" from an
    # active verification failure, for callers that want to log differently.
    unsigned: bool = False
    # Stable machine code for HTTP clients (None when ok).
    error_code: Optional[str] = None


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


def _fail(reason: str, error_code: str, *, unsigned: bool = False) -> SignatureResult:
    return SignatureResult(ok=False, reason=reason, unsigned=unsigned, error_code=error_code)


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
    expires_at = now + SESSION_KEY_TTL_SECONDS

    # Cross-dyno conflict check against Postgres when enabled.
    if _persist_enabled():
        try:
            existing_row = _db().load_signing_session_key(str(project_id), session_id)
            if existing_row is not None:
                _jwk, existing_fp, issued_at, row_expires = existing_row
                if existing_fp == fingerprint:
                    _db().upsert_signing_session_key(
                        str(project_id), session_id, public_jwk, fingerprint, now, expires_at
                    )
                elif now <= row_expires:
                    raise RegistrationError("a different key is already registered for this session")
                else:
                    _db().upsert_signing_session_key(
                        str(project_id), session_id, public_jwk, fingerprint, now, expires_at
                    )
            else:
                _db().upsert_signing_session_key(
                    str(project_id), session_id, public_jwk, fingerprint, now, expires_at
                )
        except RegistrationError:
            raise
        except Exception:
            # Fall through to in-memory — never fail registration because of
            # a transient DB blip if the local dyno can still serve traffic.
            pass

    with _lock:
        existing = _sessions.get(state_key)
        if existing is not None:
            if existing.fingerprint == fingerprint:
                existing.issued_at = now
                _sessions.move_to_end(state_key)
                return int(expires_at * 1000)
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
        return int(expires_at * 1000)


def _load_session_state(project_id: str, session_id: str, now: float):
    """Return (state, expired_flag). state is None when missing or expired."""
    state_key = (str(project_id), session_id)
    with _lock:
        state = _sessions.get(state_key)
        if state is not None:
            if now - state.issued_at > SESSION_KEY_TTL_SECONDS:
                return None, True
            return state, False

    if not _persist_enabled():
        return None, False
    try:
        row = _db().load_signing_session_key(str(project_id), session_id)
    except Exception:
        return None, False
    if row is None:
        return None, False
    public_jwk, fingerprint, issued_at, expires_at = row
    if now > expires_at:
        return None, True
    try:
        public_key, fp = _public_key_from_jwk(public_jwk)
    except RegistrationError:
        return None, False
    if fp != fingerprint:
        return None, False
    state = SessionKeyState(
        public_key=public_key,
        fingerprint=fingerprint,
        issued_at=issued_at,
        spent_nonces=OrderedDict(),
    )
    with _lock:
        _sessions[state_key] = state
        _sessions.move_to_end(state_key)
        while len(_sessions) >= _MAX_SESSIONS:
            _sessions.popitem(last=False)
    return state, False


def _header_presence(timestamp_header, nonce, signature_hex) -> tuple[int, bool]:
    """Return (count_present, all_present). Empty strings count as absent."""
    present = [
        bool(timestamp_header and str(timestamp_header).strip()),
        bool(nonce and str(nonce).strip()),
        bool(signature_hex and str(signature_hex).strip()),
    ]
    count = sum(1 for p in present if p)
    return count, count == 3


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

    present_count, all_present = _header_presence(timestamp_header, nonce, signature_hex)

    # Partial headers = tamper / broken client. Always reject (even soft mode).
    if present_count > 0 and not all_present:
        return _fail(
            "incomplete signing headers (need timestamp, nonce, and signature)",
            ERROR_SIGNING_INCOMPLETE,
        )

    if not all_present:
        if REQUEST_SIGNING_MODE == "strict":
            return _fail("request signing required", ERROR_SIGNING_REQUIRED)
        return SignatureResult(ok=True, unsigned=True)

    if not session_id:
        return _fail("missing session id", ERROR_MISSING_SESSION)
    if not project_id:
        return _fail("missing project id", ERROR_MISSING_PROJECT)
    state_key = (str(project_id), session_id)

    try:
        timestamp_ms = int(timestamp_header)
    except (TypeError, ValueError):
        return _fail("malformed timestamp", ERROR_BAD_TIMESTAMP)

    now = time.time()
    if abs(now - timestamp_ms / 1000.0) > MAX_CLOCK_SKEW_SECONDS:
        return _fail("timestamp outside allowed window", ERROR_TIMESTAMP_SKEW)

    state, expired = _load_session_state(str(project_id), session_id, now)
    if state is None:
        if expired:
            return _fail("session key expired", ERROR_KEY_EXPIRED)
        return _fail(
            "no active session key (register the public key first)",
            ERROR_NO_SESSION_KEY,
        )

    valid_until = timestamp_ms / 1000.0 + MAX_CLOCK_SKEW_SECONDS

    # Verify cryptography BEFORE consuming the nonce so a bad signature
    # cannot burn a fresh nonce (Stripe-style: authenticate then record).
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
        return _fail("signature mismatch", ERROR_SIGNATURE_MISMATCH)

    # Multi-dyno: claim nonce in Postgres (atomic). Memory is a cache.
    if _persist_enabled():
        try:
            if _db().count_signing_nonces(str(project_id), session_id) >= _MAX_NONCES_PER_SESSION:
                return _fail(
                    "too many signed requests in freshness window",
                    ERROR_NONCE_FLOOD,
                )
            if not _db().claim_signing_nonce(str(project_id), session_id, nonce, valid_until):
                return _fail("nonce already used (replay)", ERROR_NONCE_REPLAY)
        except Exception:
            # Fall back to in-memory nonce tracking on DB errors.
            pass

    with _lock:
        expired_nonces = [
            spent_nonce for spent_nonce, until in state.spent_nonces.items()
            if until < now
        ]
        for spent_nonce in expired_nonces:
            state.spent_nonces.pop(spent_nonce, None)
        if nonce in state.spent_nonces:
            return _fail("nonce already used (replay)", ERROR_NONCE_REPLAY)
        if len(state.spent_nonces) >= _MAX_NONCES_PER_SESSION:
            return _fail(
                "too many signed requests in freshness window",
                ERROR_NONCE_FLOOD,
            )
        state.spent_nonces[nonce] = valid_until
        _sessions[state_key] = state

    return SignatureResult(ok=True)


def record_predict_outcome(result: SignatureResult) -> None:
    """Update counters after a /api/predict signature check."""
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
        unsigned_share = round(unsigned / decided, 4) if decided else None
        # Ops readiness: enough samples and unsigned share under threshold.
        strict_ready = (
            decided >= MIN_SAMPLES_STRICT_READY
            and unsigned_share is not None
            and unsigned_share <= UNSIGNED_SHARE_STRICT_READY
        )
        if REQUEST_SIGNING_DISABLED:
            recommendation = "disabled_kill_switch"
        elif REQUEST_SIGNING_MODE == "strict":
            recommendation = "keep_strict"
        elif strict_ready:
            recommendation = "flip_to_strict"
        elif decided < MIN_SAMPLES_STRICT_READY:
            recommendation = "collect_more_samples"
        else:
            recommendation = "reduce_unsigned_share"

        return {
            "mode": "disabled" if REQUEST_SIGNING_DISABLED else REQUEST_SIGNING_MODE,
            "predict_signed": signed,
            "predict_unsigned": unsigned,
            "predict_rejected": rejected,
            "unsigned_share": unsigned_share,
            "strict_ready": strict_ready,
            "recommendation": recommendation,
            "unsigned_ready_threshold": UNSIGNED_SHARE_STRICT_READY,
            "min_samples_ready": MIN_SAMPLES_STRICT_READY,
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
