"""Unit tests for Phase 8: Python SDK, Webhook Signatures, and Simulator Integration (§19)."""

from __future__ import annotations

import os
import sys
import time
import pytest

# Ensure sdk/python is on sys.path
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../sdk/python"))
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from referral_client.events import PaymentSucceeded, UserRegistered
from referral_client.webhook import compute_signature, verify_signature


def test_webhook_signature_generation_and_verification() -> None:
    secret = "test_signing_secret_999"
    timestamp = int(time.time())
    payload = b'{"event_id":"evt_123","event_type":"payment.succeeded"}'

    signature = compute_signature(secret, timestamp, payload)
    assert signature.startswith("v1=")

    # Valid verification
    assert verify_signature(secret, timestamp, payload, signature) is True

    # Tampered body fails
    tampered = b'{"event_id":"evt_123","event_type":"payment.failed"}'
    assert verify_signature(secret, timestamp, tampered, signature) is False

    # Stale timestamp fails (> 300s)
    stale_timestamp = timestamp - 400
    stale_sig = compute_signature(secret, stale_timestamp, payload)
    assert verify_signature(secret, stale_timestamp, payload, stale_sig, tolerance_seconds=300) is False


def test_typed_event_envelope_generation() -> None:
    event = PaymentSucceeded(
        payment_id="pay_999",
        external_user_id="user_888",
        amount_gross=200000,
        amount_net_paid=200000,
    )
    envelope = event.to_envelope()
    assert envelope["event_type"] == "payment.succeeded"
    assert envelope["schema_version"] == 1
    assert envelope["data"]["payment_id"] == "pay_999"
    assert envelope["data"]["amount_gross"] == 200000
    assert envelope["data"]["amount_net_paid"] == 200000
