"""Authentication helpers for Safe Child (production).

Pure Python — no reflex dependency, safe to import anywhere.
Passwords: PBKDF2-HMAC-SHA256. Sessions: custom HS256 JWT.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

_ITERATIONS = 200_000
_SALT_BYTES = 16
_MIN_PASSWORD_LEN = 6


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 (200k iterations, 16-byte salt).

    Format: ``pbkdf2$200000$<salt_hex>$<hash_hex>``.
    Raises ValueError if the password is shorter than 6 characters.
    """
    if not isinstance(password, str) or len(password) < _MIN_PASSWORD_LEN:
        raise ValueError("password must be at least 6 characters long")
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash using a constant-time compare.

    Returns False for any malformed stored value — never raises.
    """
    try:
        if not isinstance(password, str) or not isinstance(stored, str):
            return False
        parts = stored.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def create_token(user_id: str, secret: str, days: int = 30) -> str:
    """Create a signed HS256 JWT: payload {sub, iat, exp}."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=days)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> str | None:
    """Decode a JWT and return the user id (``sub``), or None on any failure."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None
