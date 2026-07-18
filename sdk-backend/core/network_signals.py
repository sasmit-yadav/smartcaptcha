"""
Network-layer bot signals (strategy doc step 2 / §B.4).

The strategy doc's central point about network signals: they are the ones the
client *cannot forge* (TLS/JA4, IP/ASN, HTTP2), and commercial stacks weight
them first because a scripted client that lies about everything in the JSON
body still can't fake the TLS handshake or its source IP. This module surfaces
those signals at the app layer.

**Hard physical constraint (documented, not dodged):** the JA4/JA4H/HTTP2
fingerprints live in the TLS ClientHello and HTTP/2 preface, which are *gone*
by the time a request reaches FastAPI behind Render's TLS termination. You
cannot recompute them here. The only way to get them is an edge that captures
and forwards them as headers (Cloudflare gives JA4/JA4H/HTTP2 fingerprints as
request headers for free; a TLS-terminating proxy can too). This module
therefore:

  - READS those headers if an edge provides them (CF-* / X-JA4 / etc.) and
    scores them, and
  - NO-OPS gracefully to a 0 contribution when they're absent,

so the code path exists and lights up the moment you put an edge in front —
zero further code changes. Everything else here (client IP extraction,
datacenter/hosting reputation, non-browser UA detection) works *today* with no
edge, straight off the request.

Returns a `network_score` in 0-100 on the same scale as the behaviour and
fingerprint axes, so RiskEngine can fuse it as a fourth orthogonal signal.
"""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from typing import Optional


# --- Datacenter / hosting reputation -------------------------------------
# A seed list of well-known cloud/hosting CIDR ranges. Residential traffic
# almost never originates from these; bot farms overwhelmingly do. This is the
# "datacenter-ASN blocklist is nearly free" signal from strategy §B.4. It is
# deliberately a *seed* — the authoritative version is a GeoLite2-ASN lookup
# (set MAXMIND_ASN_DB to the .mmdb path to enable it; see _asn_is_datacenter).
# Extendable via env DATACENTER_CIDRS (comma-separated) without a code change.
_SEED_DATACENTER_CIDRS = [
    # AWS (sample of the largest ranges — full list is huge; GeoLite2 is better)
    "3.0.0.0/9", "13.32.0.0/15", "15.177.0.0/18", "18.32.0.0/11",
    "35.152.0.0/13", "52.0.0.0/11", "54.144.0.0/12", "54.224.0.0/12",
    # Google Cloud
    "34.0.0.0/9", "35.184.0.0/13", "35.192.0.0/12", "104.196.0.0/14",
    # Microsoft Azure
    "20.0.0.0/8", "40.64.0.0/10", "104.40.0.0/13", "137.116.0.0/15",
    # DigitalOcean
    "104.131.0.0/16", "159.203.0.0/16", "165.227.0.0/16", "167.71.0.0/16",
    # OVH
    "51.68.0.0/16", "51.75.0.0/16", "137.74.0.0/16", "145.239.0.0/16",
    # Hetzner
    "5.9.0.0/16", "88.198.0.0/16", "116.202.0.0/16", "168.119.0.0/16",
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

# Non-browser client signatures in the User-Agent — the cheapest catch for
# curl/requests/python/Go scrapers that don't run a browser at all.
_NON_BROWSER_UA_MARKERS = (
    "python-requests", "python-urllib", "curl/", "wget/", "go-http-client",
    "okhttp", "java/", "libwww-perl", "httpclient", "aiohttp", "node-fetch",
    "axios/", "scrapy", "postmanruntime", "insomnia",
)


@dataclass
class NetworkSignals:
    network_score: float           # 0-100, fused into overall risk
    client_ip: Optional[str]
    asn: Optional[str]             # autonomous-system number/org if resolvable
    is_datacenter_ip: bool
    non_browser_ua: bool
    ja4: Optional[str]             # TLS ClientHello fingerprint (edge-forwarded)
    ja4h: Optional[str]            # HTTP-layer fingerprint (edge-forwarded)
    http2: Optional[str]           # HTTP/2 preface fingerprint (edge-forwarded)
    ja4_present: bool
    reasons: list                  # human-readable contributing signals


def extract_client_ip(x_forwarded_for: Optional[str],
                       x_real_ip: Optional[str],
                       direct_ip: Optional[str]) -> Optional[str]:
    """Best-effort real client IP.

    Prefer the left-most X-Forwarded-For entry (the original client) when a
    proxy/edge is in front; fall back to X-Real-IP, then the direct socket
    peer. Note: XFF is spoofable when NOT behind a trusted proxy, so treat the
    IP reputation signal as advisory, never as a sole hard block.
    """
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    if x_real_ip:
        return x_real_ip.strip()
    return direct_ip


def _ip_is_datacenter(ip: Optional[str]) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_private or addr.is_loopback:
        return False  # local/dev traffic — not a datacenter signal
    for net in _DATACENTER_NETWORKS:
        if addr in net:
            return True
    return _asn_is_datacenter(addr)


def lookup_asn(ip: Optional[str]) -> Optional[str]:
    """Resolve an IP to 'AS<number> <org>' via GeoLite2-ASN if configured
    (MAXMIND_ASN_DB=/path/to/GeoLite2-ASN.mmdb), else None. Kept import-local
    so the module has no hard dependency on geoip2. This ASN is also what the
    velocity engine keys on (strategy §B.5: 'rolling counts ... by ... ASN')."""
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


def _asn_is_datacenter(addr) -> bool:
    """Authoritative datacenter check via the resolved ASN org string.
    Returns False when the DB/geoip2 isn't available — the seed CIDR list is
    the fallback."""
    asn = lookup_asn(str(addr))
    if not asn:
        return False
    org = asn.lower()
    hosting_markers = ("amazon", "google", "microsoft", "azure", "digitalocean",
                       "ovh", "hetzner", "linode", "vultr", "cloudflare",
                       "leaseweb", "contabo", "scaleway", "oracle")
    return any(m in org for m in hosting_markers)


def _extract_fp(headers: dict, keys: tuple) -> Optional[str]:
    for key in keys:
        val = headers.get(key)
        if val:
            return val.strip()
    return None


# Edge-forwarded fingerprint headers, per fingerprint layer. Cloudflare (and
# common TLS proxies) expose these under a few different names by product;
# accept the known variants. All absent without an edge -> all None.
_JA4_HEADERS = ("x-ja4", "cf-ja4", "x-ja4-fingerprint", "ja4", "x-ja3", "cf-ja3-hash")
_JA4H_HEADERS = ("x-ja4h", "cf-ja4h", "ja4h")                       # HTTP-layer
_HTTP2_HEADERS = ("x-http2-fingerprint", "cf-http2-fingerprint",    # HTTP/2 preface
                  "x-akamai-http2", "http2-fingerprint")


def evaluate_network(headers: dict, direct_ip: Optional[str] = None) -> NetworkSignals:
    """Compute the network-layer risk contribution from request headers.

    `headers` should be a case-insensitively-accessible lower-keyed dict.
    Scoring is additive and capped at 100; each signal is intentionally
    conservative (advisory) since the IP can be spoofed absent a trusted edge:
      - datacenter/hosting IP:      +55  (strong: humans rarely browse from one)
      - non-browser User-Agent:     +60  (very strong: curl/requests/etc.)
      - any fingerprint flagged:    +40  (JA4/JA4H/HTTP2 on a known-bad list —
                                          only possible when an edge supplies it)
    """
    ua = (headers.get("user-agent") or "").lower()
    ip = extract_client_ip(
        headers.get("x-forwarded-for"),
        headers.get("x-real-ip"),
        direct_ip,
    )

    reasons: list = []
    score = 0.0

    is_dc = _ip_is_datacenter(ip)
    if is_dc:
        score += 55.0
        reasons.append("datacenter/hosting source IP")

    non_browser = any(m in ua for m in _NON_BROWSER_UA_MARKERS)
    if non_browser:
        score += 60.0
        reasons.append("non-browser client User-Agent")

    # Three distinct edge-forwarded fingerprint layers (strategy §B.4: "JA4,
    # JA4H, and HTTP/2 fingerprints as request headers"). All None without an
    # edge — the signal is wired and ready, contributing nothing until then.
    ja4 = _extract_fp(headers, _JA4_HEADERS)
    ja4h = _extract_fp(headers, _JA4H_HEADERS)
    http2 = _extract_fp(headers, _HTTP2_HEADERS)
    ja4_present = ja4 is not None

    # With an edge supplying fingerprints, match each against a known-bad set
    # (env-configured, comma-separated). We don't invent verdicts for unknown
    # fingerprints — only a match on a maintained list scores.
    def _known_bad(env_name):
        return {v.strip() for v in os.getenv(env_name, "").split(",") if v.strip()}
    for label, value, env in (("JA4", ja4, "KNOWN_BAD_JA4"),
                              ("JA4H", ja4h, "KNOWN_BAD_JA4H"),
                              ("HTTP2", http2, "KNOWN_BAD_HTTP2")):
        if value and value in _known_bad(env):
            score += 40.0
            reasons.append(f"{label} fingerprint on known-bad list ({value})")

    return NetworkSignals(
        network_score=min(score, 100.0),
        client_ip=ip,
        asn=lookup_asn(ip),
        is_datacenter_ip=is_dc,
        non_browser_ua=non_browser,
        ja4=ja4,
        ja4h=ja4h,
        http2=http2,
        ja4_present=ja4_present,
        reasons=reasons,
    )
