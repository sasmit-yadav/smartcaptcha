"""Unit tests for the cross-session velocity engine (strategy step 6)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import core.velocity as velocity  # noqa: E402
from core.velocity import record_and_score, reset  # noqa: E402


def setup_function():
    reset()


def test_single_public_request_is_clean():
    r = record_and_score("86.100.20.5", "Mozilla/5.0 Chrome/137")
    assert r.velocity_score == 0.0
    assert r.ip_count == 1


def test_private_ip_ignored():
    for _ in range(500):
        r = record_and_score("127.0.0.1", "Mozilla/5.0")
    assert r.velocity_score == 0.0  # localhost never triggers velocity


def test_high_ip_volume_escalates():
    r = None
    for _ in range(velocity._IP_HARD + 5):
        r = record_and_score("86.100.20.5", "Mozilla/5.0 Chrome/137")
    assert r.velocity_score == 100.0
    assert r.ip_count >= velocity._IP_HARD
    assert any("requests from IP" in reason for reason in r.reasons)


def test_ua_rotation_flagged():
    r = None
    for i in range(velocity._UA_ROTATION_HARD + 2):
        r = record_and_score("86.100.20.5", f"Mozilla/5.0 FakeBrowser-{i}")
    assert r.velocity_score >= 80.0
    assert r.distinct_ua_count >= velocity._UA_ROTATION_HARD


def test_subnet_aggregates_multiple_ips():
    r = None
    # many requests spread across one public /24 (86.100.20.0/24 — a real,
    # non-reserved range so it isn't skipped as private), no single IP hot
    for host in range(velocity._SUBNET_HARD + 10):
        ip = f"86.100.20.{host % 256}"
        r = record_and_score(ip, "Mozilla/5.0 Chrome/137")
    assert r.subnet_count >= velocity._SUBNET_HARD
    assert r.velocity_score >= 90.0


def test_asn_aggregates_across_subnets():
    r = None
    # spread across MANY different /16s so no single IP or /24 is hot, but all
    # share one ASN — only the ASN key should light up
    for i in range(velocity._ASN_HARD + 10):
        ip = f"45.{i % 256}.{(i // 256) % 256}.{i % 251}"
        r = record_and_score(ip, "Mozilla/5.0 Chrome/137", asn="AS14061 DigitalOcean")
    assert r.asn_count >= velocity._ASN_HARD
    assert r.velocity_score >= 85.0


def test_fingerprint_hash_reappearing_flagged():
    r = None
    # same fingerprint hash across many different IPs (IP rotation, one client)
    for i in range(velocity._FP_HARD + 5):
        ip = f"77.{i % 256}.{(i // 256) % 256}.10"
        r = record_and_score(ip, "Mozilla/5.0 Chrome/137", fingerprint_hash="abc123deadbeef")
    assert r.fingerprint_count >= velocity._FP_HARD
    assert r.velocity_score >= 85.0


def test_metronomic_spacing_flagged(monkeypatch):
    # Force deterministic, perfectly-even timestamps -> CV ~ 0 -> metronomic
    ticks = iter(1000.0 + i * 2.0 for i in range(1000))
    monkeypatch.setattr(velocity.time, "time", lambda: next(ticks))
    r = None
    for _ in range(velocity._REGULARITY_MIN_SAMPLES + 5):
        r = record_and_score("86.100.20.5", "Mozilla/5.0 Chrome/137")
    assert r.interarrival_cv is not None
    assert r.interarrival_cv < velocity._REGULARITY_CV_THRESHOLD
    assert any("metronomic" in reason for reason in r.reasons)


def test_disabled_returns_zero(monkeypatch):
    monkeypatch.setattr(velocity, "VELOCITY_DISABLED", True)
    for _ in range(500):
        r = record_and_score("86.100.20.5", "Mozilla/5.0")
    assert r.velocity_score == 0.0
