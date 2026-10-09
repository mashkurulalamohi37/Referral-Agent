"""Unit and scenario tests for Phase 13: Notifications & Reporting (§16, §17, ADR 0017)."""

from __future__ import annotations

import uuid
from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.core.db import Base
from app.identity import service as identity_service
from app.notifications import service as notif_service
from app.reporting import service as reporting_service
from app.subscriptions import service as subscription_service

# Ensure all schema models are registered
import app.catalog.models  # noqa: F401
import app.commissions.models  # noqa: F401
import app.credits.models  # noqa: F401
import app.events.models  # noqa: F401
import app.identity.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.notifications.models  # noqa: F401
import app.payouts.models  # noqa: F401
import app.referrals.models  # noqa: F401
import app.reporting.models  # noqa: F401
import app.risk.models  # noqa: F401
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


async def test_notification_delivery_and_outbox(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        email="user_notif@example.com",
        display_name="Notif User",
    )

    notif, outbox = await notif_service.send_notification(
        async_session,
        user_id=user.id,
        event_key="commission.earned",
        context={"amount_bdt": "200.00"},
        channel="IN_APP",
    )

    assert notif.status == "SENT"
    assert "200.00" in notif.message
    assert outbox.status == "PENDING"
    assert outbox.payload["notification_id"] == str(notif.id)

    # Fetch user notifications
    notifs = await notif_service.get_user_notifications(async_session, user_id=user.id)
    assert len(notifs) == 1
    assert notifs[0].id == notif.id

    # Mark as read
    read_notif = await notif_service.mark_notification_read(
        async_session, notification_id=notif.id, user_id=user.id
    )
    assert read_notif.status == "READ"
    assert read_notif.read_at is not None


async def test_reporting_metrics_and_reconciliation(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos_rep",
        name="PulsePOS Reporting",
        signup_url="https://pulsepos.example.com/signup",
    )

    # Record a payment fact
    await subscription_service.record_payment_fact(
        async_session,
        product_id=product.id,
        data={
            "payment_id": "pay_recon_1",
            "external_user_id": "user_recon_1",
            "amount_gross": 200000,
            "amount_net_paid": 200000,
            "currency": "BDT",
        },
    )

    # Run daily reconciliation (1 matched, 1 missing, 1 mismatch)
    payments_to_recon = [
        {"payment_id": "pay_recon_1", "amount_net_paid": 200000},  # MATCH
        {"payment_id": "pay_missing_99", "amount_net_paid": 50000},  # MISSING
        {"payment_id": "pay_recon_1", "amount_net_paid": 150000},  # MISMATCH
    ]

    recon_run = await reporting_service.process_daily_payment_reconciliation(
        async_session,
        product_id=product.id,
        business_date=date(2026, 10, 9),
        payments=payments_to_recon,
    )

    assert recon_run.submitted_count == 3
    assert recon_run.matched_count == 1
    assert recon_run.missing_count == 1
    assert recon_run.mismatch_count == 1

    # Check dashboard metrics
    metrics = await reporting_service.get_admin_dashboard_metrics(async_session, product_id=product.id)
    assert metrics["gross_revenue_minor"] == 200000
    assert metrics["net_revenue_minor"] == 200000
