"""Unit and scenario tests for Phase 7: Subscription Credits (§11, §12, ADR 0011)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.commissions import service as commission_service
from app.core import clock
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.credits import service as credit_service
from app.identity import service as identity_service
from app.ledger import service as ledger_service

# Ensure all schema models are registered
import app.catalog.models  # noqa: F401
import app.commissions.models  # noqa: F401
import app.credits.models  # noqa: F401
import app.events.models  # noqa: F401
import app.identity.models  # noqa: F401
import app.ledger.models  # noqa: F401
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


async def test_credit_reservation_lifecycle_and_draw_priority(async_session: AsyncSession) -> None:
    # 1. Setup product and referrer with split balance (credit_only ৳100, available ৳200)
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS",
        signup_url="https://pulsepos.example.com/signup",
    )
    user = await identity_service.create_user(
        async_session,
        email="referrer@example.com",
        display_name="Referrer User",
    )
    prod_acc, _ = await catalog_service.get_or_create_product_account(
        async_session,
        product_id=product.id,
        external_user_id="cust_123",
        user_id=user.id,
    )

    # Seed wallet: 10,000 poisha credit_only, 20,000 poisha available
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=30000
    )
    await ledger_service.post_commission_confirmed(
        async_session,
        commission_id=comm_id,
        user_id=user.id,
        amount_minor=30000,
        reward_split={"WALLET": 66, "CREDIT_ONLY": 34},  # ~20000 available, ~10000 credit_only
    )

    # 2. Check spendable balance
    bal = await credit_service.get_spendable_balance(
        async_session, product_id=product.id, external_user_id="cust_123"
    )
    assert bal["spendable_minor"] == 30000
    assert bal["credit_only_minor"] > 0
    assert bal["available_minor"] > 0

    # 3. Reserve 15,000 poisha (should consume ALL credit_only first, then remainder from available)
    resv, created = await credit_service.create_reservation(
        async_session,
        product_id=product.id,
        external_user_id="cust_123",
        requested_amount=15000,
        order_ref="ord_999",
        idempotency_key="resv_key_1",
    )
    assert created is True
    assert resv.reserved_minor == 15000
    assert resv.from_credit_only_minor == bal["credit_only_minor"]
    assert resv.from_available_minor == 15000 - bal["credit_only_minor"]
    assert resv.state == "RESERVED"

    # Wallet balances after reservation: reserved = 15000, spendable = 15000
    w = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w["reserved"] == 15000
    assert w["credit_only"] == 0
    assert w["available"] == 15000

    # Idempotent reservation replay
    resv2, created2 = await credit_service.create_reservation(
        async_session,
        product_id=product.id,
        external_user_id="cust_123",
        requested_amount=15000,
        order_ref="ord_999",
        idempotency_key="resv_key_1",
    )
    assert created2 is False
    assert resv2.id == resv.id

    # 4. Partial Capture: Order only used 10,000 poisha out of 15,000 reserved
    captured = await credit_service.capture_reservation(
        async_session,
        reservation_id=resv.id,
        captured_minor=10000,
        payment_id="pay_abc123",
    )
    assert captured.state == "PARTIALLY_CAPTURED"
    assert captured.captured_minor == 10000

    # After partial capture, 5,000 uncaptured was released back to wallet
    w2 = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w2["reserved"] == 0
    assert w2["available"] == 19800
    assert w2["credit_only"] == 200


async def test_credit_release_and_expiration(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )
    user = await identity_service.create_user(
        async_session,
        email="user2@example.com",
        display_name="User Two",
    )
    await catalog_service.get_or_create_product_account(
        async_session,
        product_id=product.id,
        external_user_id="user_2",
        user_id=user.id,
    )

    # Seed wallet: 5,000 available
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=5000
    )
    await ledger_service.post_commission_confirmed(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=5000
    )

    # Reserve 5,000 with TTL
    resv, _ = await credit_service.create_reservation(
        async_session,
        product_id=product.id,
        external_user_id="user_2",
        requested_amount=5000,
        order_ref="ord_exp",
        idempotency_key="resv_exp_1",
        ttl_minutes=-5,  # Already expired in the past
    )

    # Expire stale reservations job
    expired_count = await credit_service.expire_stale_reservations(async_session)
    assert expired_count == 1

    # Check reservation state and restored wallet
    w = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w["reserved"] == 0
    assert w["available"] == 5000


async def test_credit_refund_and_limit_enforcement(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="system3",
        name="System 3",
        signup_url="https://system3.example.com/signup",
    )
    user = await identity_service.create_user(
        async_session,
        email="user3@example.com",
        display_name="User Three",
    )
    await catalog_service.get_or_create_product_account(
        async_session,
        product_id=product.id,
        external_user_id="user_3",
        user_id=user.id,
    )

    # Seed wallet: 10,000
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=10000
    )
    await ledger_service.post_commission_confirmed(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=10000
    )

    resv, _ = await credit_service.create_reservation(
        async_session,
        product_id=product.id,
        external_user_id="user_3",
        requested_amount=8000,
        order_ref="ord_ref",
        idempotency_key="resv_ref_1",
    )
    await credit_service.capture_reservation(
        async_session,
        reservation_id=resv.id,
        captured_minor=8000,
        payment_id="pay_ref_1",
    )

    # Refund 5,000 credit
    refund1, created = await credit_service.refund_credit(
        async_session,
        product_id=product.id,
        reservation_id=resv.id,
        amount_minor=5000,
        idempotency_key="rf_1",
    )
    assert created is True
    assert refund1.amount_minor == 5000

    # Refund another 3,000 (total = 8,000)
    refund2, _ = await credit_service.refund_credit(
        async_session,
        product_id=product.id,
        reservation_id=resv.id,
        amount_minor=3000,
        idempotency_key="rf_2",
    )
    assert refund2.amount_minor == 3000

    # Attempt to refund exceeding captured amount -> error
    with pytest.raises(PlatformError) as exc_info:
        await credit_service.refund_credit(
            async_session,
            product_id=product.id,
            reservation_id=resv.id,
            amount_minor=1000,
            idempotency_key="rf_3",
        )
    assert exc_info.value.code == ErrorCode.CREDIT_REFUND_EXCEEDS_CAPTURED
