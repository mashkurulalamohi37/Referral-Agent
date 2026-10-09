"""Unit and scenario tests for Phase 11: Payouts & Maker-Checker (§13, ADR 0004)."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.identity import service as identity_service
from app.ledger import service as ledger_service
from app.payouts import service as payout_service

# Ensure all schema models are registered
import app.catalog.models  # noqa: F401
import app.commissions.models  # noqa: F401
import app.credits.models  # noqa: F401
import app.events.models  # noqa: F401
import app.identity.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.payouts.models  # noqa: F401
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


async def test_payout_lifecycle_and_maker_checker(async_session: AsyncSession) -> None:
    # 1. Create user and finance admin
    user = await identity_service.create_user(
        async_session,
        email="partner@example.com",
        display_name="Partner Rahim",
    )
    admin_user = await identity_service.create_user(
        async_session,
        email="finance@example.com",
        display_name="Finance Admin",
    )

    # 2. Add payout method
    method = await payout_service.add_payout_method(
        async_session,
        user_id=user.id,
        method="bkash",
        raw_details={"phone": "01712345678"},
    )
    assert method.masked_identifier == "01*******78"
    assert method.status == "ACTIVE"

    # 3. Seed available wallet balance (৳5,000 / 500,000 poisha)
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=500000
    )
    await ledger_service.post_commission_confirmed(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=500000
    )

    # 4. Request payout of ৳2,000 (200,000 poisha)
    payout, created = await payout_service.request_payout(
        async_session,
        user_id=user.id,
        payout_method_id=method.id,
        amount_minor=200000,
        idempotency_key="pay_req_1",
    )
    assert created is True
    assert payout.amount_minor == 200000
    assert payout.state == "REQUESTED"

    # Verify wallet: Available = 300,000, Payout Hold = 200,000
    w = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w["available"] == 300000
    assert w["payout_hold"] == 200000

    # 5. Maker-checker test: User cannot approve their own payout
    with pytest.raises(PlatformError) as exc_info:
        await payout_service.approve_payout(
            async_session,
            payout_id=payout.id,
            actor_id=user.id,
            note="Self approval attempt",
        )
    assert exc_info.value.code == ErrorCode.MAKER_CHECKER_SAME_ACTOR

    # 6. Finance admin approves payout
    approved = await payout_service.approve_payout(
        async_session,
        payout_id=payout.id,
        actor_id=admin_user.id,
        note="Approved for disbursement",
    )
    assert approved.state == "APPROVED"

    # 7. Settle payout: Mark Paid
    paid = await payout_service.mark_payout_paid(
        async_session,
        payout_id=payout.id,
        provider_ref="bkash_trx_998877",
    )
    assert paid.state == "PAID"
    assert paid.provider_ref == "bkash_trx_998877"

    # Verify wallet after settlement: Payout Hold = 0, Available = 300,000
    w2 = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w2["payout_hold"] == 0
    assert w2["available"] == 300000


async def test_payout_rejection_and_fund_return(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        email="partner2@example.com",
        display_name="Partner Karim",
    )
    admin_user = await identity_service.create_user(
        async_session,
        email="admin2@example.com",
        display_name="Admin Two",
    )
    method = await payout_service.add_payout_method(
        async_session,
        user_id=user.id,
        method="bank_transfer",
        raw_details={"account_number": "1234567890"},
    )

    # Seed wallet: 200,000
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=200000
    )
    await ledger_service.post_commission_confirmed(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=200000
    )

    payout, _ = await payout_service.request_payout(
        async_session,
        user_id=user.id,
        payout_method_id=method.id,
        amount_minor=150000,
        idempotency_key="pay_req_rej",
    )

    # Reject payout
    rejected = await payout_service.reject_payout(
        async_session,
        payout_id=payout.id,
        actor_id=admin_user.id,
        reason="Bank routing number invalid",
    )
    assert rejected.state == "REJECTED"

    # Funds must be fully returned to available balance
    w = await ledger_service.get_user_wallet_balances(async_session, user_id=user.id)
    assert w["payout_hold"] == 0
    assert w["available"] == 200000


async def test_payout_csv_export(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        email="csv_user@example.com",
        display_name="CSV User",
    )
    admin = await identity_service.create_user(
        async_session,
        email="csv_admin@example.com",
        display_name="CSV Admin",
    )
    method = await payout_service.add_payout_method(
        async_session,
        user_id=user.id,
        method="nagad",
        raw_details={"phone": "01811223344"},
    )

    # Seed and request payout
    comm_id = uuid.uuid4()
    await ledger_service.post_commission_pending(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=200000
    )
    await ledger_service.post_commission_confirmed(
        async_session, commission_id=comm_id, user_id=user.id, amount_minor=200000
    )
    payout, _ = await payout_service.request_payout(
        async_session,
        user_id=user.id,
        payout_method_id=method.id,
        amount_minor=200000,
        idempotency_key="pay_csv_1",
    )
    await payout_service.approve_payout(async_session, payout_id=payout.id, actor_id=admin.id)

    csv_data = await payout_service.export_payouts_csv(async_session)
    assert "Payout ID,User ID,Method,Masked Identifier" in csv_data
    assert "nagad" in csv_data
    assert "01*******44" in csv_data
    assert "2000.00" in csv_data
