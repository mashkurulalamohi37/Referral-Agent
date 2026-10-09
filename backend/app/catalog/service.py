"""Catalog public service interface (§3 module boundaries, §21, docs/erd.md)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import ApiClient, ApiClientSecret, Plan, Product, ProductAccount
from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.core.ids import uuid7
from app.core.security import encrypt_bytes, generate_secure_token, hash_token

# ---------------------------------------------------------------- Products


async def create_product(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    signup_url: str,
    allowed_redirect_hosts: list[str] | None = None,
    attribution_window_days: int = 30,
    attribution_grace_minutes: int = 1440,
    conversion_window_days: int = 90,
    refund_window_days: int = 30,
    confirmation_days: int = 14,
    referrer_visibility: str = "MASKED",
    sensitive_category: bool = False,
    accepts_cross_product_credit: bool = True,
    credit_max_invoice_pct: int = 100,
    referral_code_required: bool = False,
    theme: dict[str, Any] | None = None,
    outbound_webhook_url: str | None = None,
    outbound_signing_secret: str | bytes | None = None,
    settings: Settings | None = None,
) -> Product:
    """Creates a new product."""
    existing = await get_product_by_slug(session, slug)
    if existing:
        raise PlatformError(ErrorCode.CONFLICT, f"Product slug '{slug}' is already registered")

    secret_enc = None
    if outbound_signing_secret:
        cfg = settings or get_settings()
        raw = outbound_signing_secret.encode("utf-8") if isinstance(outbound_signing_secret, str) else outbound_signing_secret
        secret_enc = encrypt_bytes(raw, cfg.secrets_encryption_key.get_secret_value())

    product = Product(
        slug=slug.lower().strip(),
        name=name,
        signup_url=signup_url,
        allowed_redirect_hosts=allowed_redirect_hosts or [],
        attribution_window_days=attribution_window_days,
        attribution_grace_minutes=attribution_grace_minutes,
        conversion_window_days=conversion_window_days,
        refund_window_days=refund_window_days,
        confirmation_days=confirmation_days,
        referrer_visibility=referrer_visibility,
        sensitive_category=sensitive_category,
        accepts_cross_product_credit=accepts_cross_product_credit,
        credit_max_invoice_pct=credit_max_invoice_pct,
        referral_code_required=referral_code_required,
        theme=theme,
        outbound_webhook_url=outbound_webhook_url,
        outbound_signing_secret_enc=secret_enc,
    )
    session.add(product)
    await session.flush()
    return product


async def get_product_by_id(session: AsyncSession, product_id: uuid.UUID) -> Product | None:
    """Fetches active/non-deleted product by UUID."""
    stmt = select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_slug(session: AsyncSession, slug: str) -> Product | None:
    """Fetches active/non-deleted product by unique slug."""
    stmt = select(Product).where(Product.slug == slug.lower().strip(), Product.deleted_at.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_products(session: AsyncSession, *, include_disabled: bool = False) -> list[Product]:
    """Lists non-deleted products."""
    stmt = select(Product).where(Product.deleted_at.is_(None))
    if not include_disabled:
        stmt = stmt.where(Product.status == "ACTIVE")
    result = await session.execute(stmt.order_by(Product.name))
    return list(result.scalars().all())


# ---------------------------------------------------------------- Plans


async def create_plan(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    plan_code: str,
    name: str,
    status: str = "ACTIVE",
) -> Plan:
    """Creates a plan under a product."""
    product = await get_product_by_id(session, product_id)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_id}' not found")

    existing = await get_plan_by_code(session, product_id, plan_code)
    if existing:
        raise PlatformError(ErrorCode.CONFLICT, f"Plan '{plan_code}' already exists for product")

    plan = Plan(
        product_id=product_id,
        plan_code=plan_code.strip(),
        name=name,
        status=status,
    )
    session.add(plan)
    await session.flush()
    return plan


async def get_plan_by_code(session: AsyncSession, product_id: uuid.UUID, plan_code: str) -> Plan | None:
    """Fetches a plan by product and code."""
    stmt = select(Plan).where(
        Plan.product_id == product_id,
        Plan.plan_code == plan_code.strip(),
        Plan.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_plans_for_product(session: AsyncSession, product_id: uuid.UUID) -> list[Plan]:
    """Lists plans for a product."""
    stmt = select(Plan).where(Plan.product_id == product_id, Plan.deleted_at.is_(None))
    result = await session.execute(stmt.order_by(Plan.plan_code))
    return list(result.scalars().all())


# ---------------------------------------------------------------- Product Accounts


async def get_or_create_product_account(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
    user_id: uuid.UUID | None = None,
    account_metadata: dict[str, Any] | None = None,
) -> tuple[ProductAccount, bool]:
    """Gets or creates a product account under a product."""
    product = await get_product_by_id(session, product_id)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_id}' not found")

    stmt = select(ProductAccount).where(
        ProductAccount.product_id == product_id,
        ProductAccount.external_user_id == external_user_id.strip(),
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if account:
        if user_id and account.user_id != user_id:
            account.user_id = user_id
            await session.flush()
        return account, False

    account = ProductAccount(
        product_id=product_id,
        external_user_id=external_user_id.strip(),
        user_id=user_id,
        account_metadata=account_metadata or {},
    )
    session.add(account)
    await session.flush()
    return account, True


async def get_product_account(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
) -> ProductAccount | None:
    """Looks up a product account."""
    stmt = select(ProductAccount).where(
        ProductAccount.product_id == product_id,
        ProductAccount.external_user_id == external_user_id.strip(),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_account_by_id(session: AsyncSession, account_id: uuid.UUID) -> ProductAccount | None:
    """Looks up a product account by ID."""
    stmt = select(ProductAccount).where(ProductAccount.id == account_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------- API Clients & Auth


async def register_api_client(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    name: str,
    scopes: list[str],
    settings: Settings | None = None,
) -> tuple[ApiClient, str]:
    """Registers an API client and returns the (client, plain_secret). Plain secret is never stored."""
    product = await get_product_by_id(session, product_id)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_id}' not found")

    cfg = settings or get_settings()
    key_id = f"pk_live_{generate_secure_token(16)}"
    plain_secret = f"sk_live_{generate_secure_token(32)}"
    secret_h = hash_token(plain_secret)
    secret_enc = encrypt_bytes(plain_secret.encode("utf-8"), cfg.secrets_encryption_key.get_secret_value())

    client = ApiClient(
        product_id=product_id,
        name=name,
        key_id=key_id,
        scopes=scopes,
        status="ACTIVE",
    )
    session.add(client)
    await session.flush()

    secret_record = ApiClientSecret(
        api_client_id=client.id,
        secret_hash=secret_h,
        signing_secret_enc=secret_enc,
        status="ACTIVE",
    )
    session.add(secret_record)
    await session.flush()

    return client, plain_secret


async def authenticate_api_client(
    session: AsyncSession,
    *,
    key_id: str,
    secret: str,
) -> ApiClient:
    """Authenticates API client credentials and verifies active status."""
    stmt = select(ApiClient).where(ApiClient.key_id == key_id.strip())
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    if not client or client.status != "ACTIVE":
        raise PlatformError(ErrorCode.API_CLIENT_REVOKED, "Invalid API client key or inactive client")

    secret_h = hash_token(secret.strip())
    secret_match = any(
        s.secret_hash == secret_h and s.status == "ACTIVE"
        for s in client.secrets
    )
    if not secret_match:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid API client secret")

    return client

