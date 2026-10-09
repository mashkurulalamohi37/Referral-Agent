"""Unit and security tests for Phase 2: Identity & Catalog (§2, §22.4)."""

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
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    decrypt_text,
    encrypt_text,
    hash_password,
    verify_password,
)
from app.identity import service as identity_service


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


# ---------------------------------------------------------------- Security & Crypto Primitives


def test_password_hashing_and_verification() -> None:
    pw = "SuperSecret123!"
    pw_hash = hash_password(pw)
    assert pw_hash != pw
    assert verify_password(pw, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False
    assert verify_password(pw, None) is False


def test_symmetric_encryption_roundtrip() -> None:
    key = "01234567890123456789012345678901"
    secret_text = "webhook_secret_key_9999"
    encrypted = encrypt_text(secret_text, key)
    assert encrypted != secret_text
    decrypted = decrypt_text(encrypted, key)
    assert decrypted == secret_text


def test_jwt_token_claims_and_expiration() -> None:
    settings = get_settings()
    claims = {"sub": str(uuid.uuid4()), "roles": ["ADMIN", "PARTNER"]}
    token = create_jwt_token(claims, expires_delta=timedelta(minutes=5), settings=settings)
    decoded = decode_jwt_token(token, settings=settings)
    assert decoded["sub"] == claims["sub"]
    assert decoded["roles"] == ["ADMIN", "PARTNER"]

    # Expired token test
    expired_token = create_jwt_token(claims, expires_delta=timedelta(seconds=-10), settings=settings)
    with pytest.raises(PlatformError) as exc_info:
        decode_jwt_token(expired_token, settings=settings)
    assert exc_info.value.code == ErrorCode.AUTH_TOKEN_EXPIRED


# ---------------------------------------------------------------- Identity: Users & Auth


async def test_user_creation_and_duplicate_email(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        display_name="Rahim Khan",
        email="rahim@example.com",
        password="Password123!",
        roles=["PARTNER"],
    )
    assert user.id is not None
    assert user.display_name == "Rahim Khan"
    assert user.email == "rahim@example.com"
    assert [r.role for r in user.roles] == ["PARTNER"]

    # Duplicate email rejection
    with pytest.raises(PlatformError) as exc_info:
        await identity_service.create_user(
            async_session,
            display_name="Rahim Duplicate",
            email="RAHIM@example.com",
        )
    assert exc_info.value.code == ErrorCode.CONFLICT


async def test_password_authentication(async_session: AsyncSession) -> None:
    await identity_service.create_user(
        async_session,
        display_name="Karim Ali",
        email="karim@example.com",
        password="SecurePassword456!",
    )

    # Valid auth
    authed = await identity_service.authenticate_user_password(
        async_session, email="karim@example.com", password="SecurePassword456!"
    )
    assert authed.display_name == "Karim Ali"

    # Invalid password
    with pytest.raises(PlatformError) as exc_info:
        await identity_service.authenticate_user_password(
            async_session, email="karim@example.com", password="WrongPassword!"
        )
    assert exc_info.value.code == ErrorCode.AUTH_INVALID_CREDENTIALS


async def test_refresh_token_rotation_and_family_revocation(async_session: AsyncSession) -> None:
    user = await identity_service.create_user(
        async_session,
        display_name="Token User",
        email="token@example.com",
        roles=["CUSTOMER"],
    )

    tokens = await identity_service.issue_auth_tokens(async_session, user=user)
    first_refresh = tokens["refresh_token"]

    # 1st rotation succeeds
    rotated = await identity_service.rotate_refresh_token(async_session, refresh_token=first_refresh)
    second_refresh = rotated["refresh_token"]
    assert second_refresh != first_refresh

    # 2nd rotation with new token succeeds
    third_rotation = await identity_service.rotate_refresh_token(async_session, refresh_token=second_refresh)
    assert third_rotation["refresh_token"] != second_refresh

    # REUSE ATTACK: Attacker presents the first_refresh token again!
    with pytest.raises(PlatformError) as exc_info:
        await identity_service.rotate_refresh_token(async_session, refresh_token=first_refresh)
    assert exc_info.value.code == ErrorCode.AUTH_REFRESH_REUSED

    # Legitimate user's active session is now invalidated due to breach detection
    with pytest.raises(PlatformError) as exc_info:
        await identity_service.rotate_refresh_token(
            async_session, refresh_token=third_rotation["refresh_token"]
        )
    assert exc_info.value.code == ErrorCode.AUTH_REFRESH_REUSED


async def test_sso_handoff_token_single_use_and_expiry(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="healora",
        name="Healora Health",
        signup_url="https://healora.com/signup",
    )
    account, _ = await catalog_service.get_or_create_product_account(
        async_session,
        product_id=product.id,
        external_user_id="pat_12345",
    )

    handoff_token = await identity_service.create_handoff_token(
        async_session, product_id=product.id, external_user_id="pat_12345"
    )
    assert handoff_token.startswith("hnd_")

    # 1. First exchange succeeds
    auth_data = await identity_service.exchange_handoff_token(
        async_session, handoff_token=handoff_token
    )
    assert "access_token" in auth_data
    assert "refresh_token" in auth_data

    # 2. Second exchange of the same token fails (single-use constraint)
    with pytest.raises(PlatformError) as exc_info:
        await identity_service.exchange_handoff_token(
            async_session, handoff_token=handoff_token
        )
    assert exc_info.value.code == ErrorCode.AUTH_HANDOFF_INVALID


# ---------------------------------------------------------------- Catalog: Products & Plans


async def test_catalog_products_and_plans(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pulsepos",
        name="PulsePOS Cloud",
        signup_url="https://pulsepos.com/signup",
        confirmation_days=14,
    )
    assert product.slug == "pulsepos"

    # Duplicate slug rejected
    with pytest.raises(PlatformError) as exc_info:
        await catalog_service.create_product(
            async_session,
            slug="PULSEPOS",
            name="PulsePOS Clone",
            signup_url="https://pulsepos.com/signup2",
        )
    assert exc_info.value.code == ErrorCode.CONFLICT

    # Create plans
    plan = await catalog_service.create_plan(
        async_session,
        product_id=product.id,
        plan_code="standard_monthly",
        name="Standard Monthly Plan",
    )
    assert plan.plan_code == "standard_monthly"

    plans = await catalog_service.list_plans_for_product(async_session, product.id)
    assert len(plans) == 1
    assert plans[0].name == "Standard Monthly Plan"


# ---------------------------------------------------------------- API Clients & Scopes


async def test_api_client_registration_and_authentication(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="system3",
        name="System 3 SaaS",
        signup_url="https://system3.example.com/signup",
    )

    client, secret = await catalog_service.register_api_client(
        async_session,
        product_id=product.id,
        name="System 3 Ingestion Client",
        scopes=["events:write", "referrers:enroll"],
    )
    assert client.key_id.startswith("pk_live_")
    assert secret.startswith("sk_live_")

    # Successful authentication
    authed_client = await catalog_service.authenticate_api_client(
        async_session, key_id=client.key_id, secret=secret
    )
    assert authed_client.id == client.id

    # Invalid secret
    with pytest.raises(PlatformError) as exc_info:
        await catalog_service.authenticate_api_client(
            async_session, key_id=client.key_id, secret="sk_invalid"
        )
    assert exc_info.value.code == ErrorCode.AUTH_INVALID_CREDENTIALS



# ---------------------------------------------------------------- Referrer Enrollment


async def test_referrer_enrollment_workflow(async_session: AsyncSession) -> None:
    product = await catalog_service.create_product(
        async_session,
        slug="pos_pro",
        name="POS Pro",
        signup_url="https://pospro.example.com/signup",
    )

    # 1. Enroll new user
    result = await identity_service.enroll_referrer(
        async_session,
        product_id=product.id,
        external_user_id="ext_owner_99",
        display_name="Store Owner",
        email="owner@store.com",
    )
    assert result["is_new_account"] is True
    assert "PARTNER" in result["roles"]
    assert result["external_user_id"] == "ext_owner_99"

    # 2. Re-enrolling the same external account returns existing
    second_enroll = await identity_service.enroll_referrer(
        async_session,
        product_id=product.id,
        external_user_id="ext_owner_99",
    )
    assert second_enroll["is_new_account"] is False
    assert second_enroll["user_id"] == result["user_id"]
