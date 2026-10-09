"""Unit and scenario tests for Phase 6: Refunds, Chargebacks, Renewals & Upgrades (§11, §12, §22.8)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.commissions import service as commission_service
from app.core import clock
from app.core.config import get_settings
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.identity import service as identity_service
from app.ledger import service as ledger_service
from app.referrals import service as referral_service
from app.subscriptions import service as subscription_service

# Ensure all schema tables are registered on Base.metadata
import app.catalog.models  # noqa: F401
import app.commissions.models  # noqa: F401
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


# ---------------------------------------------------------------- Proportional Refund Reversal


async def test_proportional_refund_reversals(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )
    await commission_service.create_commission_rule(
        async_session,
        rule_name="Healora 10%",
        product_id=product.id,
        rate_bps=1000,  # 10%
    )
    partner = await identity_service.create_user(
        async_session,
        display_name="Rahim Partner",
        email="rahim@partner.com",
        roles=["PARTNER"],
    )
    await referral_service.create_referral_code(
        async_session,
        user_id=partner.id,
        code="RAHIM10",
    )
    await referral_service.record_attribution(
        async_session,
        product_id=product.id,
        external_user_id="cust_refund_1",
        registered_at=clock.now(),
        referral_code="RAHIM10",
    )

    now_dt = clock.now()

    # 1. Customer pays ৳2,000 (200,000 poisha)
    await subscription_service.record_payment_fact(
        async_session,
        product_id=product.id,
        data={
            "payment_id": "pay_prop_refund",
            "external_user_id": "cust_refund_1",
            "amount_gross": 200000,
            "amount_net_paid": 200000,
            "paid_at": now_dt,
            "currency": "BDT",
        },
    )
    comm = await commission_service.process_payment_commission(
        async_session,
        product_id=product.id,
        payment_id="pay_prop_refund",
        external_user_id="cust_refund_1",
        amount_net_paid=200000,
        paid_at=now_dt,
    )
    assert comm is not None
    assert comm.amount_minor == 20000  # ৳200 commission

    # Confirm commission to AVAILABLE
    await commission_service.confirm_commission(async_session, commission_id=comm.id)
    wallet_1 = await ledger_service.get_user_wallet_balances(async_session, partner.id)
    assert wallet_1["available"] == 20000

    # 2. First partial refund of ৳500 (50,000 poisha, 25% of ৳2,000)
    # Reversal = 25% of ৳200 = ৳50 (5,000 poisha)
    comm_rev1, rev_amount1 = await commission_service.process_refund_reversal(
        async_session,
        product_id=product.id,
        payment_id="pay_prop_refund",
        refund_id="ref_part_1",
        amount_refunded=50000,
    )
    assert rev_amount1 == 5000  # ৳50 reversed
    assert comm_rev1.status == "PARTIALLY_REVERSED"

    wallet_2 = await ledger_service.get_user_wallet_balances(async_session, partner.id)
    assert wallet_2["available"] == 15000  # ৳150 remaining

    # 3. Second partial refund of remaining ৳1,500 (150,000 poisha)
    # Reversal = remaining ৳150 (15,000 poisha)
    comm_rev2, rev_amount2 = await commission_service.process_refund_reversal(
        async_session,
        product_id=product.id,
        payment_id="pay_prop_refund",
        refund_id="ref_part_2",
        amount_refunded=150000,
    )
    assert rev_amount2 == 15000
    assert comm_rev2.status == "REVERSED"

    wallet_3 = await ledger_service.get_user_wallet_balances(async_session, partner.id)
    assert wallet_3["available"] == 0


# ---------------------------------------------------------------- Negative Balance Clawback Policy


async def test_negative_balance_clawback_and_netting(async_session: AsyncSession) -> None:
    partner_id = uuid.uuid4()

    # 1. Partner has 0 balance, chargeback reversal of ৳200 occurs
    await ledger_service.post_commission_reversal(
        async_session,
        commission_id=uuid.uuid4(),
        user_id=partner_id,
        amount_minor=20000,  # ৳200
        is_pending=False,
    )

    wallet_1 = await ledger_service.get_user_wallet_balances(async_session, partner_id)
    assert wallet_1["available"] == -20000  # Negative balance (-৳200)

    # 2. Partner earns new confirmed commission of ৳300 (30,000 poisha)
    new_comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session,
        commission_id=new_comm_id,
        user_id=partner_id,
        amount_minor=30000,
    )
    await ledger_service.post_commission_confirmed(
        async_session,
        commission_id=new_comm_id,
        user_id=partner_id,
        amount_minor=30000,
    )

    # Net available balance is now: -200 + 300 = +৳100 (10,000 poisha)
    wallet_2 = await ledger_service.get_user_wallet_balances(async_session, partner_id)
    assert wallet_2["available"] == 10000


# ---------------------------------------------------------------- Renewal Windows (§9.3, §11.3)


async def test_renewal_window_eligibility(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.example.com/signup",
    )
    await commission_service.create_commission_rule(
        async_session,
        rule_name="PulsePOS Renewal 5%",
        product_id=product.id,
        billing_reason="renewal",
        rate_bps=500,  # 5%
        eligible_months_from_conversion=12,  # 12 months window
    )
    partner = await identity_service.create_user(
        async_session,
        display_name="Renewal Partner",
        email="renewal@partner.com",
        roles=["PARTNER"],
    )
    await referral_service.create_referral_code(
        async_session,
        user_id=partner.id,
        code="RENEW5",
    )

    # Customer registered on 2026-01-01
    registered_time = clock.now()
    await referral_service.record_attribution(
        async_session,
        product_id=product.id,
        external_user_id="sub_renewal_cust",
        registered_at=registered_time,
        referral_code="RENEW5",
    )

    # 1. Renewal at Month 6 (within 12 month window) -> commission created
    month_6_time = registered_time + timedelta(days=180)
    comm_valid = await commission_service.process_payment_commission(
        async_session,
        product_id=product.id,
        payment_id="pay_renewal_month6",
        external_user_id="sub_renewal_cust",
        amount_net_paid=100000,
        billing_reason="renewal",
        paid_at=month_6_time,
    )
    assert comm_valid is not None
    assert comm_valid.amount_minor == 5000  # 5% of ৳1,000 = ৳50

    # 2. Renewal at Month 15 (exceeds 12 month window) -> zero commission
    month_15_time = registered_time + timedelta(days=450)
    comm_expired = await commission_service.process_payment_commission(
        async_session,
        product_id=product.id,
        payment_id="pay_renewal_month15",
        external_user_id="sub_renewal_cust",
        amount_net_paid=100000,
        billing_reason="renewal",
        paid_at=month_15_time,
    )
    assert comm_expired is None
