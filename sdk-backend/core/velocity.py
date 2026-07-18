"""
Cross-session velocity engine (strategy doc step 6 / §B.5).

Per-session scoring is structurally blind to volume: one session can look
perfectly human while ten thousand "human" sessions from one /24 in an hour
cannot. This tracks rolling request density keyed by IP and by /24 subnet, plus
User-Agent rotation per IP, and turns it into a 0-100 velocity risk score. Like
the other network signals (and unlike anything in the JSON body), a client
can't forge its own source IP, so this catches distributed scraping and
credential-stuffing that every per-session model misses.

Implementation mirrors core/rate_limit.py deliberately: an in-process sliding
window (deque of timestamps per key) with a lock. No Redis — sdk-backend runs
as a single Render instance. If the service is ever scaled horizontally this
becomes per-instance (each sees only its share of traffic); a shared store
(Redis) would be the upgrade, same caveat the rate limiter carries.

VELOCITY_DISABLED=1 turns it off (returns 0 always).
"""
from __future__ import annotations

import ipaddress
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

VELOCITY_DISABLED = os.getenv("VELOCITY_DISABLED", "0") == "1"

# Rolling window over which request density is measured.
_WINDOW_SECONDS = int(os.getenv("VELOCITY_WINDOW_SECONDS", "300"))  # 5 min

# Per-IP requests within the window at/above which risk starts climbing, and
# the point at which it saturates to 100. Tuned conservatively — a human
# refreshing or navigating a few pages must never approach the low end.
_IP_SOFT = int(os.getenv("VELOCITY_IP_SOFT", "30"))    # ~6/min sustained
_IP_HARD = int(os.getenv("VELOCITY_IP_HARD", "120"))   # ~24/min sustained
# A /24 aggregates many hosts; thresholds are higher before it means abuse.
_SUBNET_SOFT = int(os.getenv("VELOCITY_SUBNET_SOFT", "80"))
_SUBNET_HARD = int(os.getenv("VELOCITY_SUBNET_HARD", "400"))
# Distinct User-Agents from a single IP within the window — UA rotation is a
# classic scraper tell (one host claiming to be many browsers).
_UA_ROTATION_SOFT = int(os.getenv("VELOCITY_UA_SOFT", "5"))
_UA_ROTATION_HARD = int(os.getenv("VELOCITY_UA_HARD", "20"))
# Same aggregation applied to a whole ASN (all IPs of one hosting provider).
_ASN_SOFT = int(os.getenv("VELOCITY_ASN_SOFT", "150"))
_ASN_HARD = int(os.getenv("VELOCITY_ASN_HARD", "800"))
# A single stable client fingerprint reappearing across many "sessions" is a
# strong scripted-client tell even when it rotates IPs.
_FP_SOFT = int(os.getenv("VELOCITY_FP_SOFT", "20"))
_FP_HARD = int(os.getenv("VELOCITY_FP_HARD", "100"))
# Inter-arrival regularity: metronomic request spacing (very low coefficient
# of variation of the gaps) is machine-like. Only judged once there are enough
# requests from the IP to be meaningful.
_REGULARITY_MIN_SAMPLES = int(os.getenv("VELOCITY_REGULARITY_MIN_SAMPLES", "8"))
_REGULARITY_CV_THRESHOLD = float(os.getenv("VELOCITY_REGULARITY_CV", "0.15"))

_lock = threading.Lock()
# key -> deque[timestamp]
_ip_hits: dict = {}
_subnet_hits: dict = {}
_asn_hits: dict = {}
_fp_hits: dict = {}
# ip -> {ua: last_seen_ts}
_ip_uas: dict = {}


@dataclass
class VelocityResult:
    velocity_score: float          # 0-100
    ip_count: int                  # requests from this IP in the window
    subnet_count: int              # requests from this /24 in the window
    asn_count: int                 # requests from this ASN in the window
    fingerprint_count: int         # requests from this fingerprint hash in the window
    distinct_ua_count: int         # distinct UAs from this IP in the window
    interarrival_cv: Optional[float]  # coeff. of variation of per-IP request gaps
    reasons: list = field(default_factory=list)


def _subnet_of(ip: str) -> Optional[str]:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if addr.version == 4:
        return str(ipaddress.ip_network(f"{ip}/24", strict=False))
    return str(ipaddress.ip_network(f"{ip}/48", strict=False))  # /48 for IPv6


def _prune(dq: deque, cutoff: float) -> None:
    while dq and dq[0] < cutoff:
        dq.popleft()


def _ramp(count: int, soft: int, hard: int, ceiling: float) -> float:
    """Linear ramp: 0 below `soft`, `ceiling` at/above `hard`."""
    if count <= soft:
        return 0.0
    if count >= hard:
        return ceiling
    return ceiling * (count - soft) / (hard - soft)


def _interarrival_cv(timestamps: deque) -> Optional[float]:
    """Coefficient of variation (std/mean) of the gaps between consecutive
    requests. Near 0 = metronomic (machine-like); humans are irregular
    (CV well above the threshold). None until there are enough samples."""
    if len(timestamps) < _REGULARITY_MIN_SAMPLES:
        return None
    ts = list(timestamps)
    gaps = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
    if not gaps:
        return None
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return None
    var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    return (var ** 0.5) / mean


def record_and_score(ip: Optional[str], user_agent: str = "",
                     asn: Optional[str] = None,
                     fingerprint_hash: Optional[str] = None) -> VelocityResult:
    """Record one request and return the current velocity risk.

    Keys the rolling window by IP, /24 subnet, ASN, and stable fingerprint
    hash (strategy §B.5), and computes requests/min, unique-UA-per-IP, and
    per-IP inter-arrival regularity as the velocity/entropy features.

    Private/loopback IPs (local dev, unresolved) are ignored — they'd
    otherwise pool all local traffic into one bucket and fire falsely.
    """
    empty = VelocityResult(0.0, 0, 0, 0, 0, 0, None)
    if VELOCITY_DISABLED or not ip:
        return empty
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback:
            return empty
    except ValueError:
        return empty

    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    subnet = _subnet_of(ip)

    with _lock:
        ip_dq = _ip_hits.setdefault(ip, deque())
        ip_dq.append(now)
        _prune(ip_dq, cutoff)
        ip_count = len(ip_dq)
        interarrival_cv = _interarrival_cv(ip_dq)

        subnet_count = 0
        if subnet:
            sub_dq = _subnet_hits.setdefault(subnet, deque())
            sub_dq.append(now)
            _prune(sub_dq, cutoff)
            subnet_count = len(sub_dq)

        asn_count = 0
        if asn:
            asn_dq = _asn_hits.setdefault(asn, deque())
            asn_dq.append(now)
            _prune(asn_dq, cutoff)
            asn_count = len(asn_dq)

        fp_count = 0
        if fingerprint_hash:
            fp_dq = _fp_hits.setdefault(fingerprint_hash, deque())
            fp_dq.append(now)
            _prune(fp_dq, cutoff)
            fp_count = len(fp_dq)

        ua_map = _ip_uas.setdefault(ip, {})
        if user_agent:
            ua_map[user_agent] = now
        for ua, ts in list(ua_map.items()):
            if ts < cutoff:
                del ua_map[ua]
        distinct_ua = len(ua_map)

    reasons: list = []
    ip_risk = _ramp(ip_count, _IP_SOFT, _IP_HARD, 100.0)
    if ip_risk > 0:
        reasons.append(f"{ip_count} requests from IP in {_WINDOW_SECONDS}s")
    subnet_risk = _ramp(subnet_count, _SUBNET_SOFT, _SUBNET_HARD, 90.0)
    if subnet_risk > 0:
        reasons.append(f"{subnet_count} requests from /24 in {_WINDOW_SECONDS}s")
    asn_risk = _ramp(asn_count, _ASN_SOFT, _ASN_HARD, 85.0)
    if asn_risk > 0:
        reasons.append(f"{asn_count} requests from ASN {asn} in {_WINDOW_SECONDS}s")
    fp_risk = _ramp(fp_count, _FP_SOFT, _FP_HARD, 85.0)
    if fp_risk > 0:
        reasons.append(f"{fp_count} requests from one fingerprint in {_WINDOW_SECONDS}s")
    ua_risk = _ramp(distinct_ua, _UA_ROTATION_SOFT, _UA_ROTATION_HARD, 80.0)
    if ua_risk > 0:
        reasons.append(f"{distinct_ua} distinct User-Agents from one IP")

    # Metronomic spacing: only meaningful alongside some volume, so scale it by
    # how far above the soft IP threshold we are (a few perfectly-spaced human
    # clicks must not trip it).
    regularity_risk = 0.0
    if (interarrival_cv is not None and interarrival_cv < _REGULARITY_CV_THRESHOLD
            and ip_count >= _REGULARITY_MIN_SAMPLES):
        regularity_risk = 70.0 * (1 - interarrival_cv / _REGULARITY_CV_THRESHOLD)
        reasons.append(f"metronomic request spacing (inter-arrival CV={interarrival_cv:.3f})")

    velocity_score = min(100.0, max(ip_risk, subnet_risk, asn_risk, fp_risk,
                                    ua_risk, regularity_risk))
    return VelocityResult(velocity_score, ip_count, subnet_count, asn_count,
                          fp_count, distinct_ua, interarrival_cv, reasons)


def reset() -> None:
    """Clear all windows — for tests."""
    with _lock:
        _ip_hits.clear()
        _subnet_hits.clear()
        _asn_hits.clear()
        _fp_hits.clear()
        _ip_uas.clear()
