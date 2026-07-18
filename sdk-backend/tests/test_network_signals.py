"""Unit tests for the network-signal layer (strategy step 2). Pure, no network."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.network_signals import evaluate_network, extract_client_ip  # noqa: E402


def test_residential_browser_is_clean():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",  # not in any datacenter seed range
    })
    assert net.network_score == 0.0
    assert not net.is_datacenter_ip
    assert not net.non_browser_ua


def test_non_browser_ua_flagged():
    net = evaluate_network({"user-agent": "python-requests/2.31.0"})
    assert net.non_browser_ua
    assert net.network_score >= 60.0
    assert any("non-browser" in r for r in net.reasons)


def test_datacenter_ip_flagged():
    # 3.5.0.0 is inside the AWS 3.0.0.0/9 seed range
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "3.5.6.7",
    })
    assert net.is_datacenter_ip
    assert net.network_score >= 55.0


def test_datacenter_plus_non_browser_caps_at_100():
    net = evaluate_network({
        "user-agent": "curl/8.4.0",
        "x-forwarded-for": "3.5.6.7",
    })
    assert net.network_score == 100.0  # 55 + 60 capped


def test_ja4_present_but_not_known_bad_scores_zero():
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
        "cf-ja4": "t13d1516h2_8daaf6152771_b186095e22b6",
    })
    assert net.ja4_present
    assert net.network_score == 0.0  # present but not on the known-bad list


def test_extract_client_ip_prefers_xff():
    assert extract_client_ip("1.2.3.4, 5.6.7.8", "9.9.9.9", "10.0.0.1") == "1.2.3.4"
    assert extract_client_ip(None, "9.9.9.9", "10.0.0.1") == "9.9.9.9"
    assert extract_client_ip(None, None, "10.0.0.1") == "10.0.0.1"


def test_all_three_fingerprint_layers_read(monkeypatch):
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
    assert net.network_score == 0.0  # present but none on a known-bad list


def test_known_bad_ja4h_and_http2_score(monkeypatch):
    monkeypatch.setenv("KNOWN_BAD_JA4H", "badja4h_xyz")
    monkeypatch.setenv("KNOWN_BAD_HTTP2", "badhttp2_abc")
    net = evaluate_network({
        "user-agent": "Mozilla/5.0 Chrome/137.0",
        "x-forwarded-for": "86.100.20.5",
        "x-ja4h": "badja4h_xyz",
        "x-http2-fingerprint": "badhttp2_abc",
    })
    # both fingerprint layers flagged -> 40 + 40, capped
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
