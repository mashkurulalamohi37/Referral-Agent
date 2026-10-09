"""HMAC-SHA256 webhook and event payload signing/verification (§8.1)."""

from __future__ import annotations

import hmac
import hashlib
import time


def compute_signature(signing_secret: str, timestamp: int, raw_body: bytes) -> str:
    """Computes HMAC-SHA256 signature for event intake.

    Header format: v1=<hex HMAC-SHA256(signing_secret, timestamp + "." + raw_body)>
    """
    message = f"{timestamp}.".encode("utf-8") + raw_body
    digest = hmac.new(signing_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def verify_signature(
    signing_secret: str,
    timestamp: int,
    raw_body: bytes,
    signature_header: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Verifies HMAC-SHA256 signature header with constant-time comparison and freshness check."""
    current_time = int(time.time())
    if abs(current_time - timestamp) > tolerance_seconds:
        return False

    expected_sig = compute_signature(signing_secret, timestamp, raw_body)
    return hmac.compare_digest(expected_sig, signature_header)
