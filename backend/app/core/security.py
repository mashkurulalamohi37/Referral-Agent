"""Security and cryptography primitives (§2, §22.3, ADR 0003)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError

# ---------------------------------------------------------------- Password Hashing


def hash_password(password: str) -> str:
    """Hashes a password with bcrypt and returns a UTF-8 string."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- Symmetric Encryption (AES-GCM)


def _derive_key(secret: str | bytes, length: int = 32) -> bytes:
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if len(secret) == length:
        return secret
    return hashlib.sha256(secret).digest()[:length]


def encrypt_bytes(data: bytes, key: str | bytes) -> bytes:
    """Encrypts data using AES-256-GCM. Returns nonce (12 bytes) + ciphertext/tag."""
    aesgcm = AESGCM(_derive_key(key))
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_bytes(encrypted: bytes, key: str | bytes) -> bytes:
    """Decrypts data encrypted with encrypt_bytes."""
    if len(encrypted) < 28:  # 12 nonce + 16 tag minimum
        raise PlatformError(ErrorCode.VALIDATION_ERROR, "Encrypted payload is invalid or corrupted")
    aesgcm = AESGCM(_derive_key(key))
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:
        raise PlatformError(
            ErrorCode.VALIDATION_ERROR, "Decryption failed (invalid key or ciphertext)"
        ) from exc


def encrypt_text(text: str, key: str | bytes) -> str:
    """Encrypts text and returns urlsafe base64 string."""
    encrypted = encrypt_bytes(text.encode("utf-8"), key)
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_text(encrypted_b64: str, key: str | bytes) -> str:
    """Decrypts base64-encoded ciphertext produced by encrypt_text."""
    raw = base64.urlsafe_b64decode(encrypted_b64.encode("utf-8"))
    return decrypt_bytes(raw, key).decode("utf-8")


# ---------------------------------------------------------------- Tokens & Signatures


def generate_secure_token(length_bytes: int = 32) -> str:
    """Generates a cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(length_bytes)


def hash_token(token: str) -> bytes:
    """Returns SHA-256 digest of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).digest()


def sign_hmac_sha256(payload: bytes, secret: str | bytes) -> str:
    """Computes HMAC-SHA256 hex digest for request signatures or webhooks."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_hmac_sha256(payload: bytes, secret: str | bytes, signature: str) -> bool:
    """Constant-time verification of HMAC-SHA256 signature."""
    expected = sign_hmac_sha256(payload, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------- JWT


def create_jwt_token(
    payload: dict[str, Any],
    *,
    expires_delta: timedelta,
    settings: Settings | None = None,
) -> str:
    """Encodes a JWT with exp, iat, and given claims using HS256."""
    cfg = settings or get_settings()
    now_dt = clock.now()
    claims = {
        **payload,
        "iat": int(now_dt.timestamp()),
        "exp": int((now_dt + expires_delta).timestamp()),
    }
    key = cfg.jwt_signing_key.get_secret_value()
    return jwt.encode(claims, key, algorithm="HS256")


def decode_jwt_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decodes and validates a JWT token."""
    cfg = settings or get_settings()
    key = cfg.jwt_signing_key.get_secret_value()
    try:
        return jwt.decode(token, key, algorithms=["HS256"])  # type: ignore[no-any-return]
    except jwt.ExpiredSignatureError as exc:
        raise PlatformError(ErrorCode.AUTH_TOKEN_EXPIRED, "Authentication token has expired") from exc
    except jwt.PyJWTError as exc:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Authentication token is invalid") from exc

