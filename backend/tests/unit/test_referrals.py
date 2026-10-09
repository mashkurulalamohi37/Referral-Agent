"""Unit and security tests for Phase 3: Referrals & Attribution (§6, §7, §22.5)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.catalog import service as catalog_service
from app.core import clock
from app.core.config import get_settings
from app.core.db import Base
from app.core.errors import ErrorCode, PlatformError
from app.identity import service as identity_service
from app.referrals import service as referral_service


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


# ---------------------------------------------------------------- Code Generation & Validation


async def test_referral_code_generation_and_uniqueness(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim@example.com",
        roles=["PARTNER"],
    )

    # 1. Default code generation
    default_code = await referral_service.create_referral_code(
        async_session,
        user_id=user.id,
    )
    assert default_code.code.startswith("RAHIM")
    assert len(default_code.code) >= 7
    assert default_code.is_vanity is False

    # 2. Vanity code creation
    vanity = await referral_service.create_referral_code(
        async_session,
        user_id=user.id,
        code="RAHIM82",
    )
    assert vanity.code == "RAHIM82"
    assert vanity.is_vanity is True

    # 3. Duplicate code rejection (case-insensitive)
    with pytest.raises(PlatformError) as exc_info:
        await referral_service.create_referral_code(
            async_session,
            user_id=user.id,
            code="rahim82",
        )
    assert exc_info.value.code == ErrorCode.REFERRAL_CODE_TAKEN

    # 4. Reserved words rejection
    for reserved in ["ADMIN", "API", "ROOT", "SIGNUP", "PORTAL"]:
        with pytest.raises(PlatformError) as exc_info:
            await referral_service.create_referral_code(
                async_session,
                user_id=user.id,
                code=reserved,
            )
        assert exc_info.value.code == ErrorCode.REFERRAL_CODE_FORBIDDEN


# ---------------------------------------------------------------- Click Tracking & Attribution Token


async def test_click_tracking_and_cross_domain_attribution_token(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim.partner@example.com",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=user.id,
        code="RAHIM82",
    )

    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )

    # Record click
    click_res = await referral_service.record_click(
        async_session,
        code_str="rahim82",
        client_ip="103.120.45.10",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        product_slug="healora",
        campaign="OCT2026",
        utm_source="twitter",
        utm_medium="social",
    )

    assert click_res["code"] == "RAHIM82"
    assert click_res["product_slug"] == "healora"
    token = click_res["attribution_token"]
    assert token is not None

    # Redirect URL verification (strictly from product's registered signup_url)
    redirect_url = click_res["redirect_url"]
    assert redirect_url.startswith("https://healora.example.com/signup")
    assert "ref=RAHIM82" in redirect_url
    assert f"rt={token}" in redirect_url
    assert "utm_source=twitter" in redirect_url

    # Decode and verify claims in attribution token
    claims = referral_service.decode_attribution_token(token)
    assert claims["code"] == "RAHIM82"
    assert claims["product"] == "healora"
    assert claims["campaign"] == "OCT2026"
    assert claims["click_id"] == click_res["click_id"]


# ---------------------------------------------------------------- Attribution Ingestion & Rules


async def test_attribution_ingestion_and_idempotency(async_session: AsyncSession) -> None:
    referrer = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim.partner@example.com",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=referrer.id,
        code="RAHIM82",
    )
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )

    click_res = await referral_service.record_click(
        async_session,
        code_str="RAHIM82",
        client_ip="103.120.45.10",
        user_agent="Mozilla/5.0",
        product_slug="healora",
    )
    attr_token = click_res["attribution_token"]

    now_dt = clock.now()

    # 1. Ingest attribution
    attribution, is_new = await referral_service.record_attribution(
        async_session,
        product_id=product.id,
        external_user_id="HLR-456",
        registered_at=now_dt,
        referral_code="RAHIM82",
        attribution_token=attr_token,
        signals={"ip": "103.120.45.10", "email": "karim@example.com"},
    )
    assert is_new is True
    assert attribution.status == "ATTRIBUTED"
    assert attribution.external_user_id == "HLR-456"
    assert attribution.referrer_user_id == referrer.id
    assert attribution.expires_at == now_dt + timedelta(days=30)

    # 2. Idempotent second ingestion returns existing (is_new=False)
    second_attr, is_new_second = await referral_service.record_attribution(
        async_session,
        product_id=product.id,
        external_user_id="HLR-456",
        registered_at=now_dt,
        referral_code="RAHIM82",
    )
    assert is_new_second is False
    assert second_attr.id == attribution.id


# ---------------------------------------------------------------- Self-Referral Prevention


async def test_self_referral_prevention_rules(async_session: AsyncSession) -> None:
    referrer = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim@example.com",
        phone="+8801711000000",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=referrer.id,
        code="RAHIM82",
    )
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )

    now_dt = clock.now()

    # 1. Reject matching email
    with pytest.raises(PlatformError) as exc_info:
        await referral_service.record_attribution(
            async_session,
            product_id=product.id,
            external_user_id="HLR-OWNER",
            registered_at=now_dt,
            referral_code="RAHIM82",
            signals={"email": "rahim@example.com"},
        )
    assert exc_info.value.code == ErrorCode.SELF_REFERRAL

    # 2. Reject matching phone
    with pytest.raises(PlatformError) as exc_info:
        await referral_service.record_attribution(
            async_session,
            product_id=product.id,
            external_user_id="HLR-OWNER-2",
            registered_at=now_dt,
            referral_code="RAHIM82",
            signals={"phone": "+8801711000000"},
        )
    assert exc_info.value.code == ErrorCode.SELF_REFERRAL


# ---------------------------------------------------------------- Grace Period & Expiry


async def test_attribution_grace_window_validation(async_session: AsyncSession) -> None:
    referrer = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim.partner@example.com",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=referrer.id,
        code="RAHIM82",
    )
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.example.com/signup",
    )

    # 1. Registered 3 hours ago (exceeds default 60 min grace window)
    stale_time = clock.now() - timedelta(hours=3)
    with pytest.raises(PlatformError) as exc_info:
        await referral_service.record_attribution(
            async_session,
            product_id=product.id,
            external_user_id="HLR-OLD-USER",
            registered_at=stale_time,
            referral_code="RAHIM82",
        )
    assert exc_info.value.code == ErrorCode.ATTRIBUTION_NOT_NEW_ACCOUNT

    # 2. Registered in future
    future_time = clock.now() + timedelta(hours=1)
    with pytest.raises(PlatformError) as exc_info:
        await referral_service.record_attribution(
            async_session,
            product_id=product.id,
            external_user_id="HLR-FUTURE",
            registered_at=future_time,
            referral_code="RAHIM82",
        )
    assert exc_info.value.code == ErrorCode.ATTRIBUTION_TIMESTAMP_INVALID


# ---------------------------------------------------------------- Public Code Validation


async def test_public_code_lookup_and_user_codes_list(async_session: AsyncSession) -> None:
    partner = await identity_service.create_user(
        async_session,
        display_name="Tariq Hasan",
        email="tariq@example.com",
        roles=["PARTNER"],
    )
    code = await referral_service.create_referral_code(
        async_session,
        user_id=partner.id,
        code="TARIQ99",
    )

    # 1. Lookup active code
    found = await referral_service.get_referral_code_by_code(async_session, "tariq99")
    assert found is not None
    assert found.code == "TARIQ99"

    # 2. Lookup non-existent code
    non_existent = await referral_service.get_referral_code_by_code(async_session, "DOESNOTEXIST")
    assert non_existent is None

    # 3. List partner's codes
    codes = await referral_service.list_referral_codes_for_user(async_session, partner.id)
    assert len(codes) == 1
    assert codes[0].code == "TARIQ99"
