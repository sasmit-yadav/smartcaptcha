"""
Network-layer bot signals (strategy / freeze doc P1).

Signals the client *cannot forge* from the JSON body: source IP (when behind
a trusted edge), ASN/org (MaxMind or Cloudflare-forwarded), non-browser UA,
and edge TLS/HTTP fingerprints when present.

Cloudflare plan reality (verified 2026-07 against CF docs):
  - Free: Bot Fight Mode only — does NOT forward cf-bot-score / cf-ja4 to origin.
  - Free Worker CAN read request.cf (asn, asOrganization, tlsVersion, …) and
    forward them as custom headers (see tools/cloudflare/forward-cf-headers.js).
  - Enterprise Bot Management: managed transform adds cf-bot-score, cf-ja4, etc.

This module:
  - Prefers cf-connecting-ip when the zone is orange-clouded (trusted).
  - Scores CF Worker / Enterprise headers when present; no-ops when absent.
  - Keeps CIDR seed + optional MaxMind ASN for deployments without a Worker.

Returns network_score 0-100 for RiskEngine fusion.
"""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from typing import Optional


# --- Datacenter / hosting reputation -------------------------------------
_SEED_DATACENTER_CIDRS = [
    "3.0.0.0/9", "13.32.0.0/15", "15.177.0.0/18", "18.32.0.0/11",
    "35.152.0.0/13", "52.0.0.0/11", "54.144.0.0/12", "54.224.0.0/12",
    "34.0.0.0/9", "35.184.0.0/13", "35.192.0.0/12", "104.196.0.0/14",
    "20.0.0.0/8", "40.64.0.0/10", "104.40.0.0/13", "137.116.0.0/15",
    "104.131.0.0/16", "159.203.0.0/16", "165.227.0.0/16", "167.71.0.0/16",
    "51.68.0.0/16", "51.75.0.0/16", "137.74.0.0/16", "145.239.0.0/16",
    "5.9.0.0/16", "88.198.0.0/16", "116.202.0.0/16", "168.119.0.0/16",
    # Extra common bot-farm hosts
    "45.33.0.0/16", "45.56.0.0/16", "45.79.0.0/16",  # Linode-ish
    "66.228.0.0/16", "69.164.0.0/16",
]


def _load_datacenter_networks() -> list:
    cidrs = list(_SEED_DATACENTER_CIDRS)
    extra = os.getenv("DATACENTER_CIDRS", "")
    for c in extra.split(","):
        c = c.strip()
        if c:
            cidrs.append(c)
    nets = []
    for c in cidrs:
        try:
            nets.append(ipaddress.ip_network(c, strict=False))
        except ValueError:
            continue
    return nets


_DATACENTER_NETWORKS = _load_datacenter_networks()

_NON_BROWSER_UA_MARKERS = (
    "python-requests", "python-urllib", "curl/", "wget/", "go-http-client",
    "okhttp", "java/", "libwww-perl", "httpclient", "aiohttp", "node-fetch",
    "axios/", "scrapy", "postmanruntime", "insomnia", "httpx/", "undici",
)

_HOSTING_ORG_MARKERS = (
    "amazon", "aws", "google", "microsoft", "azure", "digitalocean",
    "ovh", "hetzner", "linode", "akamai", "vultr", "cloudflare",
    "leaseweb", "contabo", "scaleway", "oracle", "alibaba", "tencent",
    "huawei", "choopa", "m247", "psychz", "colocrossing", "hostinger",
    "hetzner online", "amazon.com", "google cloud", "microsoft corporation",
)


@dataclass
class NetworkSignals:
    network_score: float
    client_ip: Optional[str]
    asn: Optional[str]
    is_datacenter_ip: bool
    non_browser_ua: bool
    ja4: Optional[str]
    ja4h: Optional[str]
    http2: Optional[str]
    ja4_present: bool
    cf_edge_seen: bool = False
    cf_bot_score: Optional[int] = None
    cf_as_org: Optional[str] = None
    cf_tls_version: Optional[str] = None
    reasons: list = field(default_factory=list)


def extract_client_ip(
    x_forwarded_for: Optional[str],
    x_real_ip: Optional[str],
    direct_ip: Optional[str],
    cf_connecting_ip: Optional[str] = None,
) -> Optional[str]:
    """Best-effort real client IP.

    When Cloudflare proxies the zone, `CF-Connecting-IP` is the trusted
    eyeball address (set by CF, not the client). Prefer it over XFF, which
    is spoofable unless the edge strips client-supplied values.
    """
    if cf_connecting_ip and str(cf_connecting_ip).strip():
        return str(cf_connecting_ip).strip()
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    if x_real_ip:
        return x_real_ip.strip()
    return direct_ip


def _ip_in_datacenter_cidrs(ip: Optional[str]) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_private or addr.is_loopback:
        return False
    for net in _DATACENTER_NETWORKS:
        if addr in net:
            return True
    return False


def lookup_asn(ip: Optional[str]) -> Optional[str]:
    """Resolve IP to 'AS<number> <org>' via GeoLite2-ASN if configured."""
    if not ip:
        return None
    db_path = os.getenv("MAXMIND_ASN_DB")
    if not db_path or not os.path.exists(db_path):
        return None
    try:
        import geoip2.database  # type: ignore
        with geoip2.database.Reader(db_path) as reader:
            rec = reader.asn(str(ip))
        num = rec.autonomous_system_number
        org = rec.autonomous_system_organization or ""
        return f"AS{num} {org}".strip()
    except Exception:
        return None


def _org_looks_hosting(org: Optional[str]) -> bool:
    if not org:
        return False
    low = org.lower()
    return any(m in low for m in _HOSTING_ORG_MARKERS)


def _extract_fp(headers: dict, keys: tuple) -> Optional[str]:
    for key in keys:
        val = headers.get(key)
        if val:
            return val.strip()
    return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


# Enterprise Bot Management / managed transforms (absent on Free).
_JA4_HEADERS = ("x-ja4", "cf-ja4", "x-ja4-fingerprint", "ja4", "x-ja3", "cf-ja3-hash")
_JA4H_HEADERS = ("x-ja4h", "cf-ja4h", "ja4h")
_HTTP2_HEADERS = (
    "x-http2-fingerprint", "cf-http2-fingerprint",
    "x-akamai-http2", "http2-fingerprint",
)
# Free Worker forwarder (tools/cloudflare/forward-cf-headers.js) + common aliases.
_CF_ASN_HEADERS = ("x-vp-cf-asn", "cf-asn", "x-asn")
_CF_AS_ORG_HEADERS = ("x-vp-cf-as-org", "cf-as-organization", "x-as-organization")
_CF_TLS_HEADERS = ("x-vp-cf-tls-version", "cf-tls-version", "x-tls-version")
_CF_HTTP_PROTO_HEADERS = ("x-vp-cf-http-protocol", "cf-http-protocol")
_CF_BOT_SCORE_HEADERS = ("cf-bot-score", "x-bot-score", "x-vp-cf-bot-score")
_CF_VERIFIED_BOT_HEADERS = ("cf-verified-bot", "x-vp-cf-verified-bot")


def evaluate_network(headers: dict, direct_ip: Optional[str] = None) -> NetworkSignals:
    """Compute network-layer risk from request headers (lower-cased keys)."""
    ua = (headers.get("user-agent") or "").lower()
    cf_connecting = headers.get("cf-connecting-ip")
    ip = extract_client_ip(
        headers.get("x-forwarded-for"),
        headers.get("x-real-ip"),
        direct_ip,
        cf_connecting_ip=cf_connecting,
    )

    reasons: list = []
    score = 0.0

    # --- Cloudflare edge presence (Free orange-cloud) --------------------
    cf_ray = headers.get("cf-ray")
    cf_edge_seen = bool(cf_connecting or cf_ray or headers.get("cf-visitor"))
    if cf_edge_seen:
        reasons.append("cloudflare edge headers present")

    # Worker / Enterprise ASN org (works on Free when Worker forwards it).
    cf_asn_num = _extract_fp(headers, _CF_ASN_HEADERS)
    cf_as_org = _extract_fp(headers, _CF_AS_ORG_HEADERS)
    cf_tls = _extract_fp(headers, _CF_TLS_HEADERS)
    cf_http_proto = _extract_fp(headers, _CF_HTTP_PROTO_HEADERS)
    cf_bot_score = _parse_int(_extract_fp(headers, _CF_BOT_SCORE_HEADERS))
    cf_verified_bot = (_extract_fp(headers, _CF_VERIFIED_BOT_HEADERS) or "").lower()

    asn_from_db = lookup_asn(ip)
    asn = None
    if cf_asn_num and cf_as_org:
        asn = f"AS{cf_asn_num} {cf_as_org}".strip()
    elif cf_asn_num:
        asn = f"AS{cf_asn_num}"
    elif cf_as_org:
        asn = cf_as_org
    else:
        asn = asn_from_db

    is_dc = _ip_in_datacenter_cidrs(ip) or _org_looks_hosting(cf_as_org) or _org_looks_hosting(asn)
    if is_dc:
        # Slightly stronger when CF ASN org confirms hosting (harder to spoof
        # than client XFF alone when CF-Connecting-IP is trusted).
        bump = 60.0 if (cf_as_org and _org_looks_hosting(cf_as_org) and cf_edge_seen) else 55.0
        score += bump
        reasons.append("datacenter/hosting source IP or ASN")

    non_browser = any(m in ua for m in _NON_BROWSER_UA_MARKERS)
    if non_browser:
        score += 60.0
        reasons.append("non-browser client User-Agent")

    # Enterprise bot score (1-99, low = bot). Soft-weight; never sole block
    # unless extremely low — humans can score oddly on VPNs.
    if cf_bot_score is not None:
        if cf_verified_bot in ("true", "1", "yes"):
            reasons.append("cloudflare verified bot")
        elif cf_bot_score <= 5:
            score += 70.0
            reasons.append(f"cf-bot-score definite bot ({cf_bot_score})")
        elif cf_bot_score <= 29:
            score += 45.0
            reasons.append(f"cf-bot-score likely bot ({cf_bot_score})")
        elif cf_bot_score <= 49:
            score += 20.0
            reasons.append(f"cf-bot-score elevated ({cf_bot_score})")

    # TLS / HTTP protocol from Free Worker forwarder — scrapers often odd.
    if cf_tls:
        tls_l = cf_tls.lower()
        if tls_l in ("tlsv1", "tlsv1.0", "tlsv1.1", "none", ""):
            score += 25.0
            reasons.append(f"weak or missing TLS ({cf_tls})")
    if cf_http_proto:
        proto = cf_http_proto.lower()
        if proto in ("http/1.0", "http/0.9"):
            score += 15.0
            reasons.append(f"obsolete HTTP protocol ({cf_http_proto})")

    ja4 = _extract_fp(headers, _JA4_HEADERS)
    ja4h = _extract_fp(headers, _JA4H_HEADERS)
    http2 = _extract_fp(headers, _HTTP2_HEADERS)
    ja4_present = ja4 is not None

    def _known_bad(env_name: str) -> set:
        return {v.strip() for v in os.getenv(env_name, "").split(",") if v.strip()}

    for label, value, env in (
        ("JA4", ja4, "KNOWN_BAD_JA4"),
        ("JA4H", ja4h, "KNOWN_BAD_JA4H"),
        ("HTTP2", http2, "KNOWN_BAD_HTTP2"),
    ):
        if value and value in _known_bad(env):
            score += 40.0
            reasons.append(f"{label} fingerprint on known-bad list ({value})")

    # Deduplicate reasons that fire on every CF request (edge present is info).
    # Keep "cloudflare edge headers present" only when nothing else scored —
    # otherwise strip it so a clean residential CF user stays at 0.
    if score == 0.0 and "cloudflare edge headers present" in reasons:
        reasons = []
    elif "cloudflare edge headers present" in reasons and score > 0:
        reasons = [r for r in reasons if r != "cloudflare edge headers present"]

    return NetworkSignals(
        network_score=min(score, 100.0),
        client_ip=ip,
        asn=asn,
        is_datacenter_ip=is_dc,
        non_browser_ua=non_browser,
        ja4=ja4,
        ja4h=ja4h,
        http2=http2,
        ja4_present=ja4_present,
        cf_edge_seen=cf_edge_seen,
        cf_bot_score=cf_bot_score,
        cf_as_org=cf_as_org,
        cf_tls_version=cf_tls,
        reasons=reasons,
    )


def fuse_network_and_velocity(
    network_score: float,
    velocity_score: float,
    *,
    is_datacenter_ip: bool = False,
) -> float:
    """P1.2: fuse per-request network risk with cross-session velocity.

    max() alone is kept as the floor (any axis can block). When traffic is
    already from hosting ASN/IP *and* velocity is elevated, amplify so farms
    that drip just under a single threshold still cross 50.
    """
    base = max(float(network_score or 0), float(velocity_score or 0))
    if is_datacenter_ip and velocity_score >= 20:
        amplified = min(100.0, velocity_score * 1.35 + 15.0)
        base = max(base, amplified)
    if network_score >= 40 and velocity_score >= 30:
        base = max(base, min(100.0, (network_score + velocity_score) / 2 + 15.0))
    return min(100.0, base)
