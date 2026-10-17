# -*- coding: utf-8 -*-
"""Authentication primitives for Aegis-Core.

* Password hashing: PBKDF2-HMAC-SHA256 (100 000 iterations, 32-byte salt).
* Token generation: HMAC-SHA256 signed JSON payloads encoded in URL-safe
  Base64 — a lightweight JWT-like scheme that requires **zero** external
  dependencies.

The ``SECRET_KEY`` is read from the ``AEGIS_SECRET_KEY`` environment variable.
If it is not set, a random 64-byte hex key is generated *once* and persisted
to ``<project_root>/backend/.secret_key`` so it survives restarts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Secret key management
# ---------------------------------------------------------------------------

_KEY_FILE = Path(__file__).resolve().parent / ".secret_key"


def _load_or_create_secret() -> str:
    """Return a stable secret key, generating one if necessary.

    Priority:
    1. ``AEGIS_SECRET_KEY`` environment variable
    2. Persisted key in ``backend/.secret_key``
    3. Newly generated random key (saved for reuse)
    """
    env_key = os.environ.get("AEGIS_SECRET_KEY")
    if env_key:
        return env_key

    if _KEY_FILE.exists():
        try:
            return _KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            pass  # Fall through and regenerate

    key = os.urandom(64).hex()
    try:
        _KEY_FILE.write_text(key, encoding="utf-8")
    except OSError:
        pass  # Ephemeral key — acceptable in dev
    return key


SECRET_KEY: str = _load_or_create_secret()

# ---------------------------------------------------------------------------
# Password hashing  (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

_HASH_ALGORITHM = "sha256"
_HASH_ITERATIONS = 100_000
_SALT_LENGTH = 32  # bytes
_DK_LENGTH = 64    # derived-key bytes


def hash_password(password: str) -> str:
    """Hash *password* with a fresh random salt.

    Returns a string in the format ``salt_hex$dk_hex`` that is safe to store
    in the database.
    """
    salt = os.urandom(_SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
        dklen=_DK_LENGTH,
    )
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify *password* against *stored_hash* produced by :func:`hash_password`.

    Uses ``hmac.compare_digest`` for constant-time comparison to mitigate
    timing attacks.
    """
    try:
        salt_hex, dk_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(dk_hex)
    except (ValueError, AttributeError):
        return False

    dk = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
        dklen=_DK_LENGTH,
    )
    return hmac.compare_digest(dk, expected_dk)


# ---------------------------------------------------------------------------
# Token creation / verification  (HMAC-SHA256 signed JSON)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """URL-safe Base64 encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """URL-safe Base64 decoding (re-adds padding)."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(payload_b64: str) -> str:
    """Create an HMAC-SHA256 signature for the given Base64 payload."""
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(user_id: str, expires_hours: int = 24) -> str:
    """Create a short-lived access token for *user_id*.

    The token is a dot-separated string: ``<payload_b64>.<signature>``.
    """
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": time.time(),
        "exp": time.time() + expires_hours * 3600,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def create_refresh_token(user_id: str, expires_hours: int = 720) -> str:
    """Create a long-lived refresh token (default 30 days)."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": time.time(),
        "exp": time.time() + expires_hours * 3600,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify *token*.

    Returns the payload ``dict`` if the signature is valid **and** the token
    has not expired.  Returns ``None`` otherwise.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig = parts
        expected_sig = _sign(payload_b64)

        if not hmac.compare_digest(sig, expected_sig):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload: dict = json.loads(payload_bytes)

        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None
