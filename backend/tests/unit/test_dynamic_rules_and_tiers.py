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

def test_customer_tenure_decay_and_server_cost_adjustment() -> None:
    """Tests commission rate changing over customer lifetime (e.g. 2y/3y tenure decay due to server costs)."""
    rule = CommissionRule(
        rule_name="SaaS Recurring Commission with Tenure Decay",
        commission_type="PERCENTAGE",
        rate_bps=2000,  # Base rate 20%
        eligible_months_from_conversion=36,  # 3-year maximum eligible lifetime
        tier_schedule={
            "tenure_tiers": [
                {"tenure_name": "Year 1 (Months 1-12)", "min_month": 1, "max_month": 12, "rate_bps": 2000},
                {"tenure_name": "Year 2 (Months 13-24)", "min_month": 13, "max_month": 24, "rate_bps": 1500},
                {"tenure_name": "Year 3 (Months 25-36)", "min_month": 25, "max_month": 36, "rate_bps": 1000},
                {"tenure_name": "Year 4+ (Beyond 36m)", "min_month": 37, "max_month": None, "rate_bps": 0},
            ],
        },
    )

    # 10,000 BDT subscription (1,000,000 minor)
    # Month 6 (Year 1): 20% = 200,000 minor
    y1 = commission_service.calculate_commission_amount(1000000, rule, customer_tenure_months=6)
    assert y1 == 200000

    # Month 18 (Year 2 - server cost increased): 15% = 150,000 minor
    y2 = commission_service.calculate_commission_amount(1000000, rule, customer_tenure_months=18)
    assert y2 == 150000

    # Month 30 (Year 3 - infra cost & maintenance): 10% = 100,000 minor
    y3 = commission_service.calculate_commission_amount(1000000, rule, customer_tenure_months=30)
    assert y3 == 100000

    # Month 40 (Year 4 - beyond eligible cutoff): 0 minor (sunset)
    y4 = commission_service.calculate_commission_amount(1000000, rule, customer_tenure_months=40)
    assert y4 == 0

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
