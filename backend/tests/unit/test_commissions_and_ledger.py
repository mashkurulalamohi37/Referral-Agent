"""Unit and acceptance tests for Phase 5: Commissions & Ledger Engine (§9, §10, §22.7)."""

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


# ---------------------------------------------------------------- Double-Entry Ledger Invariant I1


async def test_ledger_double_entry_balance_enforcement(async_session: AsyncSession) -> None:
    user_id = uuid.uuid4()

    # 1. Unbalanced transaction rejected (Invariant I1)
    with pytest.raises(PlatformError) as exc_info:
        await ledger_service.post_journal_transaction(
            async_session,
            transaction_type="ADJUSTMENT",
            idempotency_key="unbalanced_tx_1",
            description="Bad unbalanced posting",
            entries=[
                {"account_number": "platform:commission_expense:BDT", "amount": 1000},
                {"account_number": f"user:pending:{user_id}:BDT", "amount": -800},  # Sum = +200 != 0
            ],
        )
    assert exc_info.value.code == ErrorCode.LEDGER_UNBALANCED

    # 2. Balanced transaction accepted
    tx, is_new = await ledger_service.post_journal_transaction(
        async_session,
        transaction_type="ADJUSTMENT",
        idempotency_key="balanced_tx_1",
        description="Good balanced posting",
        entries=[
            {"account_number": "platform:commission_expense:BDT", "amount": 1000},
            {"account_number": f"user:pending:{user_id}:BDT", "amount": -1000},
        ],
    )
    assert is_new is True
    assert tx.idempotency_key == "balanced_tx_1"

    # Verify wallet balances
    balances = await ledger_service.get_user_wallet_balances(async_session, user_id)
    assert balances["pending"] == 1000
    assert balances["available"] == 0


# ---------------------------------------------------------------- Rule Specificity & Tie-Breaking


async def test_rule_specificity_scoring_and_tie_breaking(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.example.com/signup",
    )

    partner = await identity_service.create_user(
        async_session,
        display_name="VIP Partner",
        email="vip@partner.com",
        roles=["PARTNER"],
    )

    # 1. Generic product rule (10%)
    generic_rule = await commission_service.create_commission_rule(
        async_session,
        rule_name="PulsePOS Standard 10%",
        product_id=product.id,
        rate_bps=1000,
    )

    # 2. Specific VIP partner rule (20%)
    vip_rule = await commission_service.create_commission_rule(
        async_session,
        rule_name="VIP Partner 20%",
        product_id=product.id,
        partner_id=partner.id,
        rate_bps=2000,
    )

    # Resolution for non-VIP partner gets generic rule
    other_user_id = uuid.uuid4()
    resolved_generic = await commission_service.resolve_commission_rule(
        async_session,
        product_id=product.id,
        partner_id=other_user_id,
    )
    assert resolved_generic.id == generic_rule.id
    assert resolved_generic.rate_bps == 1000

    # Resolution for VIP partner gets VIP rule (partner_id bitmask wins)
    resolved_vip = await commission_service.resolve_commission_rule(
        async_session,
        product_id=product.id,
        partner_id=partner.id,
    )
    assert resolved_vip.id == vip_rule.id
    assert resolved_vip.rate_bps == 2000

    # 3. Create tied rule with exact same score -> raises COMMISSION_RULE_TIE
    await commission_service.create_commission_rule(
        async_session,
        rule_name="VIP Partner 20% Duplicate Tie",
        product_id=product.id,
        partner_id=partner.id,
        rate_bps=2500,
    )

    with pytest.raises(PlatformError) as exc_info:
        await commission_service.resolve_commission_rule(
            async_session,
            product_id=product.id,
            partner_id=partner.id,
        )
    assert exc_info.value.code == ErrorCode.COMMISSION_RULE_TIE


# ---------------------------------------------------------------- Acceptance Scenario A (§1)


async def test_acceptance_scenario_a_end_to_end(async_session: AsyncSession) -> None:
    """End-to-End Acceptance Scenario A (§1):

    Rahim enrolls as referrer -> gets code RAHIM82.
    Karim opens /r/RAHIM82?product=healora -> click recorded -> redirect.
    Karim signs up -> attribution recorded.
    Karim pays ৳2,000 for Healora Premium -> 10% rule resolved -> ৳200 PENDING (ledger posted).
    Confirmation period passes -> commission AVAILABLE (ledger posted).
    Rahim sees ৳200 available balance in wallet.
    """
    # 1. Product setup
    healora = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
        confirmation_days=14,
    )

    # 2. Commission Rule (10% = 1000 bps)
    await commission_service.create_commission_rule(
        async_session,
        rule_name="Healora Standard 10%",
        product_id=healora.id,
        rate_bps=1000,
        confirmation_days=14,
    )

    # 3. Rahim enrolls as partner
    enroll_result = await identity_service.enroll_referrer(
        async_session,
        product_id=healora.id,
        external_user_id="rahim_owner",
        display_name="Rahim Khan",
        email="rahim@example.com",
    )
    rahim_user_id = uuid.UUID(enroll_result["user_id"])

    rahim_code = await referral_service.create_referral_code(
        async_session,
        user_id=rahim_user_id,
        code="RAHIM82",
    )
    assert rahim_code.code == "RAHIM82"

    # 4. Click tracking & attribution token
    click_res = await referral_service.record_click(
        async_session,
        code_str="RAHIM82",
        client_ip="103.1.2.3",
        user_agent="Mozilla/5.0",
        product_slug="healora",
    )
    attr_token = click_res["attribution_token"]

    # 5. Karim signs up on Healora (Attribution)
    now_dt = clock.now()
    attribution, is_new_attr = await referral_service.record_attribution(
        async_session,
        product_id=healora.id,
        external_user_id="karim_patient_77",
        registered_at=now_dt,
        referral_code="RAHIM82",
        attribution_token=attr_token,
        signals={"email": "karim@example.com"},
    )
    assert is_new_attr is True
    assert attribution.status == "ATTRIBUTED"

    # 6. Karim pays ৳2,000 (200,000 poisha)
    # Commission calculation: 200,000 * 10% = 20,000 poisha (৳200)
    commission = await commission_service.process_payment_commission(
        async_session,
        product_id=healora.id,
        payment_id="pay_healora_1001",
        external_user_id="karim_patient_77",
        amount_net_paid=200000,
        plan_code="premium_monthly",
        billing_reason="initial",
        paid_at=now_dt,
    )
    assert commission is not None
    assert commission.amount_minor == 20000  # ৳200
    assert commission.status == "PENDING"

    # Check Rahim's wallet balance: pending = ৳200 (20,000 poisha), available = 0
    wallet_1 = await ledger_service.get_user_wallet_balances(async_session, rahim_user_id)
    assert wallet_1["pending"] == 20000
    assert wallet_1["available"] == 0

    # 7. Confirmation period passes (14 days)
    confirmed_comm = await commission_service.confirm_commission(
        async_session,
        commission_id=commission.id,
    )
    assert confirmed_comm.status == "AVAILABLE"
    assert confirmed_comm.confirmed_at is not None

    # Check Rahim's wallet balance: pending = 0, available = ৳200 (20,000 poisha)
    wallet_2 = await ledger_service.get_user_wallet_balances(async_session, rahim_user_id)
    assert wallet_2["pending"] == 0
    assert wallet_2["available"] == 20000
    assert wallet_2["total_earned"] == 20000


# ---------------------------------------------------------------- Commission Reversal


async def test_commission_reversal_on_refund(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.example.com/signup",
    )
    await commission_service.create_commission_rule(
        async_session,
        rule_name="Standard 10%",
        product_id=product.id,
        rate_bps=1000,
    )
    partner = await identity_service.create_user(
        async_session,
        display_name="Partner Ali",
        email="ali@example.com",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=partner.id,
        code="ALI99",
    )
    await referral_service.record_attribution(
        async_session,
        product_id=product.id,
        external_user_id="cust_1",
        registered_at=clock.now(),
        referral_code="ALI99",
    )

    # 1. Earn and confirm commission
    comm = await commission_service.process_payment_commission(
        async_session,
        product_id=product.id,
        payment_id="pay_refund_test",
        external_user_id="cust_1",
        amount_net_paid=100000,  # ৳1,000 -> ৳100 (10,000 poisha)
    )
    assert comm is not None
    await commission_service.confirm_commission(async_session, commission_id=comm.id)

    wallet_before = await ledger_service.get_user_wallet_balances(async_session, partner.id)
    assert wallet_before["available"] == 10000

    # 2. Refund happens -> reverse commission
    reversed_comm = await commission_service.reverse_commission(async_session, commission_id=comm.id)
    assert reversed_comm.status == "REVERSED"

    wallet_after = await ledger_service.get_user_wallet_balances(async_session, partner.id)
    assert wallet_after["available"] == 0
