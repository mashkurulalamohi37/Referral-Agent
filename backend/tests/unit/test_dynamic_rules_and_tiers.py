"""Unit tests for Dynamic Commission Rules, Progressive Volume Tiers, and Agent Types."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.commissions import service as commission_service
from app.commissions.models import CommissionRule
from app.core.db import Base
from app.identity import service as identity_service

# Ensure schemas are registered
import app.catalog.models
import app.commissions.models
import app.identity.models
import app.ledger.models
import app.referrals.models


@pytest.fixture
async def async_session() -> AsyncSession:
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


def test_progressive_volume_tier_calculation() -> None:
    """Tests tiered calculation for sales 1-50 vs 51+ with milestone bonus."""
    rule = CommissionRule(
        rule_name="PulsePOS Volume Tier",
        commission_type="TIERED",
        rate_bps=1000,
        tier_schedule={
            "type": "PROGRESSIVE_VOLUME",
            "tiers": [
                {"tier_number": 1, "min_count": 1, "max_count": 50, "rate_bps": 1000, "fixed_bonus_minor": 0},
                {"tier_number": 2, "min_count": 51, "max_count": 100, "rate_bps": 1500, "fixed_bonus_minor": 500000},
            ],
        },
    )

    # Sale #1 (10,000 BDT = 1,000,000 minor) -> 10% = 100,000 minor
    c1 = commission_service.calculate_commission_amount(1000000, rule, sale_count=1)
    assert c1 == 100000

    # Sale #50 -> 10% = 100,000 minor
    c50 = commission_service.calculate_commission_amount(1000000, rule, sale_count=50)
    assert c50 == 100000

    # Sale #51 -> 15% (150,000) + 5,000 BDT milestone bonus (500,000) = 650,000 minor
    c51 = commission_service.calculate_commission_amount(1000000, rule, sale_count=51)
    assert c51 == 650000

    # Sale #52 -> 15% (150,000) (bonus was for threshold milestone) = 150,000 minor
    c52 = commission_service.calculate_commission_amount(1000000, rule, sale_count=52)
    assert c52 == 150000


async def test_dynamic_rule_crud(async_session: AsyncSession) -> None:
    """Tests dynamic creation, update and archiving of rules without redeployment."""
    rule = await commission_service.create_commission_rule(
        async_session,
        rule_name="Dynamic Rule 1",
        partner_type="INDIVIDUAL",
        commission_type="PERCENTAGE",
        rate_bps=1000,
    )
    assert rule.id is not None
    assert rule.rate_bps == 1000

    # Update dynamically to 12%
    updated = await commission_service.update_commission_rule(
        async_session,
        rule.id,
        rate_bps=1200,
        partner_type="COMPANY",
    )
    assert updated.rate_bps == 1200
    assert updated.partner_type == "COMPANY"

    # List rules
    rules = await commission_service.list_commission_rules(async_session, partner_type="COMPANY")
    assert len(rules) == 1
    assert rules[0].id == rule.id

    # Archive rule
    archived = await commission_service.delete_commission_rule(async_session, rule.id)
    assert archived is True
    check = await commission_service.get_commission_rule_by_id(async_session, rule.id)
    assert check.status == "ARCHIVED"
