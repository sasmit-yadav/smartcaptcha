"""
Hand-rolled in-process fixed-window rate limiter.

No Redis — sdk-backend runs as a single Render instance, so an in-memory
dict + lock is sufficient and avoids an extra infra dependency. Not safe to
use as-is if the service is ever scaled to multiple instances (each instance
would enforce its own window).

RATE_LIMIT_DISABLED=1 fully disables all limiting (e.g. local dev).
"""

import os
import time
import threading
from typing import Optional

from fastapi import HTTPException, Request

RATE_LIMIT_DISABLED = os.getenv("RATE_LIMIT_DISABLED", "0") == "1"

_lock = threading.Lock()
# {(bucket_name, identity): (window_start_epoch_seconds, count)}
_windows: dict = {}


def _client_ip(request: Request) -> str:
    # Render sits behind a proxy; the first hop in X-Forwarded-For is the
    # original client.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check(bucket: str, identity: str, limit: int, window_seconds: int = 60) -> Optional[int]:
    """Returns None if allowed, or seconds-until-reset if rate limited."""
    if RATE_LIMIT_DISABLED:
        return None

    key = (bucket, identity)
    now = time.time()
    with _lock:
        window_start, count = _windows.get(key, (now, 0))
        if now - window_start >= window_seconds:
            window_start, count = now, 0
        count += 1
        _windows[key] = (window_start, count)
        if count > limit:
            return max(1, int(window_seconds - (now - window_start)))
    return None


def enforce(bucket: str, identity: str, limit: int, window_seconds: int = 60):
    """Raise 429 with Retry-After if `identity` has exceeded `limit` in the window."""
    retry_after = _check(bucket, identity, limit, window_seconds)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(bucket: str, limit: int, window_seconds: int = 60, by: str = "ip"):
    """
    FastAPI dependency factory. `by` is 'ip' (default) or 'key' — callers
    using 'key' must also check a second IP-based dependency themselves if
    they want both limits (see predict.py: per-key + per-IP).
    """

    def _dep(request: Request):
        if by == "ip":
            enforce(bucket, _client_ip(request), limit, window_seconds)
        return None

    return _dep
