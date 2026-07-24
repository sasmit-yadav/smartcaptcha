"""
Password policy for dashboard signup (OWASP ASVS / Authentication Cheat Sheet).

- Prefer length over complex composition rules.
- Min 12 characters (ASVS strongly recommends ≥15; 12 is a practical SaaS floor).
- Allow up to 72 bytes (bcrypt limit) — reject longer rather than silently truncate.
- Block a small built-in list of extremely common passwords.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

MIN_PASSWORD_LENGTH = 12
# bcrypt only uses the first 72 bytes; never silently truncate.
MAX_PASSWORD_BYTES = 72

# Compact denylist — common / breached-style passwords. Keep lowercase.
_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password123",
        "password1234",
        "password12345",
        "123456789012",
        "1234567890123",
        "qwertyuiopas",
        "qwerty123456",
        "letmein12345",
        "welcome12345",
        "adminadmin12",
        "iloveyou1234",
        "monkey123456",
        "dragon123456",
        "master123456",
        "loginlogin12",
        "abcabcabcabc",
        "veilproof123",
        "veilproof1234",
        "changeme1234",
        "passw0rd1234",
        "p@ssw0rd1234",
        "football1234",
        "baseball1234",
        "sunshine1234",
        "princess1234",
        "trustno1!!!!",
        "access123456",
        "shadow123456",
        "michael12345",
        "jennifer1234",
        "computer1234",
        "superman1234",
        "batmanbatman",
        "aaaaaaaaaaaa",
        "111111111111",
        "000000000000",
    }
)

_EMAIL_RE = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    normalized = normalize_email(email)
    if not normalized or len(normalized) > 254:
        return False, "Enter a valid email address"
    if not _EMAIL_RE.match(normalized):
        return False, "Enter a valid email address"
    return True, None


def validate_password(password: str, email: str = "") -> Tuple[bool, Optional[str]]:
    if password is None:
        return False, "Password is required"
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        return False, f"Password must be at most {MAX_PASSWORD_BYTES} bytes"
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return False, "Choose a less common password"
    local = normalize_email(email).split("@", 1)[0]
    if local and len(local) >= 4 and local in lowered:
        return False, "Password must not contain your email name"
    # Reject all-whitespace / all-same-char
    if password.strip() == "" or len(set(password)) == 1:
        return False, "Choose a stronger password"
    return True, None
