"""Unit and scenario tests for Phase 12: Risk & Fraud Engine (§14, ADR 0005)."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.identity import service as identity_service
from app.risk import service as risk_service

# Ensure all schema models are registered
import app.catalog.models  # noqa: F401
import app.commissions.models  # noqa: F401
import app.credits.models  # noqa: F401
import app.events.models  # noqa: F401
import app.identity.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.payouts.models  # noqa: F401
import app.referrals.models  # noqa: F401
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


async def test_risk_signal_hashing_and_ip_prefix() -> None:
    h1 = risk_service.hash_risk_signal("user@example.com", "EMAIL")
    h2 = risk_service.hash_risk_signal("USER@EXAMPLE.COM ", "EMAIL")
    assert h1 == h2  # Canonicalized before hashing

    # IP prefix calculation
    prefix_h = risk_service.extract_ip_prefix_hash("192.168.1.100")
    assert prefix_h is not None
    prefix_h2 = risk_service.extract_ip_prefix_hash("192.168.1.200")
    assert prefix_h == prefix_h2  # Same /24 subnet produces matching prefix hash


async def test_risk_evaluation_and_fraud_detection(async_session: AsyncSession) -> None:
    # 1. Create referrer and record their known signals
    referrer = await identity_service.create_user(
        async_session,
        email="referrer@example.com",
        display_name="Referrer One",
    )
    await risk_service.record_signals(
        async_session,
        user_id=referrer.id,
        signals={
            "email": "referrer@example.com",
            "phone": "+8801700000000",
            "ip": "203.0.113.10",
        },
    )

    # 2. Referred user with shared email and IP -> HIGH risk
    referred_signals_high = {
        "email": "referrer@example.com",  # Shared email!
        "ip": "203.0.113.10",
    }
    level, score, reasons = await risk_service.evaluate_risk_for_referral(
        async_session,
        referrer_user_id=referrer.id,
        referred_signals=referred_signals_high,
    )
    assert level == "HIGH"
    assert score >= 100
    assert any(r["rule"] == "SHARED_EMAIL" for r in reasons)

    # User now has open high risk hold
    has_hold = await risk_service.has_open_high_risk_hold(async_session, user_id=referrer.id)
    assert has_hold is True

    # 3. Risk analyst reviews and clears the case
    cases = await risk_service.get_risk_cases(async_session, status="OPEN")
    assert len(cases) == 1
    case = cases[0]

    analyst = await identity_service.create_user(
        async_session,
        email="analyst@example.com",
        display_name="Risk Analyst",
    )
    resolved = await risk_service.decide_risk_case(
        async_session,
        case_id=case.id,
        actor_id=analyst.id,
        decision="CLEARED",
        note="False positive confirmed via ID verification",
    )
    assert resolved.status == "CLEARED"

    # User no longer has open high risk hold
    has_hold_after = await risk_service.has_open_high_risk_hold(async_session, user_id=referrer.id)
    assert has_hold_after is False
