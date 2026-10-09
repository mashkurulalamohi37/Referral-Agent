"""Unit and security tests for Phase 4: Inbound Events, Outbox, and Subscriptions (§8, §22.6)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.core import clock
from app.core.config import get_settings
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.events import service as event_service
from app.subscriptions import service as subscription_service

# Ensure all schema tables are registered on Base.metadata
import app.catalog.models  # noqa: F401
import app.events.models  # noqa: F401
import app.identity.models  # noqa: F401
import app.referrals.models  # noqa: F401
import app.subscriptions.models  # noqa: F401


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provides an in-memory SQLite async database session with full schema tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ---------------------------------------------------------------- Signature Verification


def test_signature_computation_and_verification() -> None:
    secret = "whsec_test_secret_12345678901234567890"
    raw_body = b'{"event_id":"evt_1","event_type":"user.registered"}'
    now_ts = int(clock.now().timestamp())

    # 1. Valid signature
    sig = event_service.compute_signature(secret, now_ts, raw_body)
    assert sig.startswith("v1=")
    event_service.verify_signature(
        secret=secret,
        timestamp_header=str(now_ts),
        signature_header=sig,
        raw_body=raw_body,
    )

    # 2. Corrupted body
    with pytest.raises(PlatformError) as exc_info:
        event_service.verify_signature(
            secret=secret,
            timestamp_header=str(now_ts),
            signature_header=sig,
            raw_body=b'{"event_id":"evt_TAMPERED"}',
        )
    assert exc_info.value.code == ErrorCode.SIGNATURE_INVALID

    # 3. Timestamp drift > 300s
    stale_ts = now_ts - 305
    stale_sig = event_service.compute_signature(secret, stale_ts, raw_body)
    with pytest.raises(PlatformError) as exc_info:
        event_service.verify_signature(
            secret=secret,
            timestamp_header=str(stale_ts),
            signature_header=stale_sig,
            raw_body=raw_body,
        )
    assert exc_info.value.code == ErrorCode.SIGNATURE_TIMESTAMP_STALE


# ---------------------------------------------------------------- JSON Schema Validation


def test_event_json_schema_validation() -> None:
    # 1. Valid user.registered
    valid_user_reg = {
        "external_user_id": "usr_100",
        "registered_at": "2026-10-09T00:00:00Z",
        "signals": {"ip": "103.1.1.1"},
    }
    event_service.validate_event_data("user.registered", valid_user_reg)

    # 2. Valid payment.succeeded
    valid_payment = {
        "payment_id": "pay_999",
        "subscription_id": "sub_111",
        "external_user_id": "usr_100",
        "plan_code": "premium_monthly",
        "billing_reason": "initial",
        "currency": "BDT",
        "amount_gross": 200000,
        "discount_amount": 0,
        "tax_amount": 0,
        "credit_applied_amount": 0,
        "amount_net_paid": 200000,
        "paid_at": "2026-10-09T00:00:00Z",
    }
    event_service.validate_event_data("payment.succeeded", valid_payment)

    # 3. Extra forbidden field
    invalid_payment = dict(valid_payment)
    invalid_payment["unexpected_field"] = "hacker"
    with pytest.raises(PlatformError) as exc_info:
        event_service.validate_event_data("payment.succeeded", invalid_payment)
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    # 4. Unsupported event type
    with pytest.raises(PlatformError) as exc_info:
        event_service.validate_event_data("unknown.fake.event", {})
    assert exc_info.value.code == ErrorCode.EVENT_TYPE_UNSUPPORTED


# ---------------------------------------------------------------- Inbound Intake & Idempotency


async def test_event_intake_idempotency_and_outbox(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.example.com/signup",
    )

    now_iso = clock.now().isoformat()
    period_end_iso = (clock.now() + timedelta(days=30)).isoformat()

    payload = {
        "event_id": "evt_pulse_001",
        "event_type": "subscription.created",
        "schema_version": 1,
        "occurred_at": now_iso,
        "data": {
            "subscription_id": "sub_abc_123",
            "external_user_id": "usr_pos_55",
            "plan_code": "retail_pro",
            "status": "active",
            "period_start": now_iso,
            "period_end": period_end_iso,
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # 1. First ingestion succeeds
    inbound, is_new = await event_service.ingest_event(
        async_session,
        product_id=product.id,
        raw_body=raw_body,
        payload_dict=payload,
        verify_sig=False,
    )
    assert is_new is True
    assert inbound.event_id == "evt_pulse_001"
    assert inbound.status == "PROCESSED"

    # Derived subscription was created
    sub = await subscription_service.get_subscription(
        async_session, product_id=product.id, subscription_id="sub_abc_123"
    )
    assert sub is not None
    assert sub.plan_code == "retail_pro"

    # 2. Idempotent replay of same event returns existing
    second_inbound, is_new_second = await event_service.ingest_event(
        async_session,
        product_id=product.id,
        raw_body=raw_body,
        payload_dict=payload,
        verify_sig=False,
    )
    assert is_new_second is False
    assert second_inbound.id == inbound.id

    # 3. Conflict: same event_id with different payload
    altered_payload = dict(payload)
    altered_payload["data"] = {
        "subscription_id": "sub_DIFFERENT",
        "external_user_id": "usr_pos_55",
        "plan_code": "retail_pro",
        "status": "active",
        "period_start": now_iso,
        "period_end": period_end_iso,
    }
    altered_raw = json.dumps(altered_payload).encode("utf-8")
    with pytest.raises(PlatformError) as exc_info:
        await event_service.ingest_event(
            async_session,
            product_id=product.id,
            raw_body=altered_raw,
            payload_dict=altered_payload,
            verify_sig=False,
        )
    assert exc_info.value.code == ErrorCode.EVENT_ID_CONFLICT


# ---------------------------------------------------------------- Business Key Conflicts


async def test_business_key_conflicts(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.example.com/signup",
    )

    now_iso = clock.now().isoformat()
    pay_data = {
        "payment_id": "pay_unique_100",
        "subscription_id": "sub_pos_1",
        "external_user_id": "usr_99",
        "plan_code": "retail_pro",
        "billing_reason": "initial",
        "currency": "BDT",
        "amount_gross": 500000,
        "discount_amount": 0,
        "tax_amount": 0,
        "credit_applied_amount": 0,
        "amount_net_paid": 500000,
        "paid_at": now_iso,
    }

    event_1 = {
        "event_id": "evt_payment_first",
        "event_type": "payment.succeeded",
        "schema_version": 1,
        "occurred_at": now_iso,
        "data": pay_data,
    }
    raw_1 = json.dumps(event_1).encode("utf-8")

    await event_service.ingest_event(
        async_session,
        product_id=product.id,
        raw_body=raw_1,
        payload_dict=event_1,
        verify_sig=False,
    )

    # Attempt to ingest different event_id for the same payment_id
    event_2 = {
        "event_id": "evt_payment_SECOND",
        "event_type": "payment.succeeded",
        "schema_version": 1,
        "occurred_at": now_iso,
        "data": pay_data,
    }
    raw_2 = json.dumps(event_2).encode("utf-8")
    with pytest.raises(PlatformError) as exc_info:
        await event_service.ingest_event(
            async_session,
            product_id=product.id,
            raw_body=raw_2,
            payload_dict=event_2,
            verify_sig=False,
        )
    assert exc_info.value.code == ErrorCode.BUSINESS_KEY_CONFLICT
