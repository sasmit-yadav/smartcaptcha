"""Unit tests for the network-signal layer (P1 Cloudflare + velocity fuse)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.network_signals import (  # noqa: E402
    evaluate_network,
    extract_client_ip,
    fuse_network_and_velocity,
)


def test_residential_browser_is_clean():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
    })
    assert net.network_score == 0.0
    assert not net.is_datacenter_ip
    assert not net.non_browser_ua


def test_cf_edge_alone_does_not_raise_score():
    """Orange-cloud residential humans must stay at 0."""
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "cf-connecting-ip": "86.100.20.5",
        "cf-ray": "8a1b2c3d4e5f6g7h-BOM",
    })
    assert net.cf_edge_seen
    assert net.client_ip == "86.100.20.5"
    assert net.network_score == 0.0


def test_cf_connecting_ip_preferred_over_spoofed_xff():
    assert extract_client_ip(
        "1.2.3.4, 5.6.7.8", "9.9.9.9", "10.0.0.1", cf_connecting_ip="86.100.20.5"
    ) == "86.100.20.5"


def test_non_browser_ua_flagged():
    net = evaluate_network({"user-agent": "python-requests/2.31.0"})
    assert net.non_browser_ua
    assert net.network_score >= 60.0
    assert any("non-browser" in r for r in net.reasons)


def test_datacenter_ip_flagged():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "3.5.6.7",
    })
    assert net.is_datacenter_ip
    assert net.network_score >= 55.0


def test_worker_forwarded_hosting_asn_flags_residential_looking_ip():
    """Free Worker forwards asOrganization — catches hosting even if CIDR miss."""
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "cf-connecting-ip": "86.100.20.5",
        "cf-ray": "abc123-BOM",
        "x-vp-cf-asn": "16509",
        "x-vp-cf-as-org": "Amazon.com, Inc.",
    })
    assert net.is_datacenter_ip
    assert net.cf_as_org and "Amazon" in net.cf_as_org
    assert net.network_score >= 60.0
    assert "AS16509" in (net.asn or "")


def test_cf_bot_score_likely_bot():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "cf-connecting-ip": "86.100.20.5",
        "cf-bot-score": "15",
    })
    assert net.cf_bot_score == 15
    assert net.network_score >= 45.0


def test_cf_bot_score_verified_bot_not_penalized_as_hard():
    net = evaluate_network({
        "user-agent": "Googlebot/2.1",
        "cf-connecting-ip": "86.100.20.5",
        "cf-bot-score": "1",
        "cf-verified-bot": "true",
    })
    # Verified bots skip the low-score penalty path.
    assert net.network_score < 70.0 or any("verified bot" in r for r in net.reasons)


def test_weak_tls_from_worker_header():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "cf-connecting-ip": "86.100.20.5",
        "x-vp-cf-tls-version": "TLSv1",
    })
    assert net.network_score >= 25.0


def test_datacenter_plus_non_browser_caps_at_100():
    net = evaluate_network({
        "user-agent": "curl/8.4.0",
        "x-forwarded-for": "3.5.6.7",
    })
    assert net.network_score == 100.0


def test_ja4_present_but_not_known_bad_scores_zero():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
        "cf-ja4": "t13d1516h2_8daaf6152771_b186095e22b6",
    })
    assert net.ja4_present
    assert net.network_score == 0.0


def test_extract_client_ip_prefers_xff_without_cf():
    assert extract_client_ip("1.2.3.4, 5.6.7.8", "9.9.9.9", "10.0.0.1") == "1.2.3.4"
    assert extract_client_ip(None, "9.9.9.9", "10.0.0.1") == "9.9.9.9"
    assert extract_client_ip(None, None, "10.0.0.1") == "10.0.0.1"


def test_all_three_fingerprint_layers_read():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
        "cf-ja4": "t13d1516h2_8daaf6152771_b186095e22b6",
        "cf-ja4h": "ge11nn08enus_9a3f1c",
        "cf-http2-fingerprint": "1:65536,2:0,4:131072,6:262144|m,a,s,p",
    })
    assert net.ja4 is not None
    assert net.ja4h is not None
    assert net.http2 is not None
    assert net.network_score == 0.0


def test_known_bad_ja4h_and_http2_score(monkeypatch):
    monkeypatch.setenv("KNOWN_BAD_JA4H", "badja4h_xyz")
    monkeypatch.setenv("KNOWN_BAD_HTTP2", "badhttp2_abc")
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
        "x-ja4h": "badja4h_xyz",
        "x-http2-fingerprint": "badhttp2_abc",
    })
    assert net.network_score >= 40.0
    assert any("JA4H" in r for r in net.reasons)
    assert any("HTTP2" in r for r in net.reasons)


def test_private_ip_not_datacenter():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "127.0.0.1",
    })
    assert not net.is_datacenter_ip
    assert net.network_score == 0.0


def test_fuse_amplifies_datacenter_velocity():
    # Velocity alone below 50; with DC amplify should cross block band.
    fused = fuse_network_and_velocity(20.0, 40.0, is_datacenter_ip=True)
    assert fused >= 50.0
    assert fused > max(20.0, 40.0)


def test_fuse_clean_residential_stays_low():
    assert fuse_network_and_velocity(0.0, 0.0, is_datacenter_ip=False) == 0.0
    assert fuse_network_and_velocity(0.0, 10.0, is_datacenter_ip=False) == 10.0
