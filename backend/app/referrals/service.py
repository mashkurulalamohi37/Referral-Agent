"""Referral service: codes, clicks, links, and attribution (§6, §7, docs/erd.md)."""

from __future__ import annotations

import hashlib
import re
import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.core.ids import uuid7
from app.core.security import create_jwt_token, decode_jwt_token
from app.identity import service as identity_service
from app.referrals.models import Attribution, ReferralClick, ReferralCode

# Crockford Base32-inspired alphabet (no 0, O, 1, I, L)
REFERRAL_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

RESERVED_CODES = {
    "ADMIN",
    "API",
    "AUTH",
    "LOGIN",
    "LOGOUT",
    "REGISTER",
    "SIGNUP",
    "TERMS",
    "PRIVACY",
    "PORTAL",
    "SUPPORT",
    "HELP",
    "R",
    "REF",
    "ROOT",
    "WWW",
    "REFERRAL",
    "COMMISSION",
    "PAYOUT",
    "SYSTEM",
    "NULL",
    "UNDEFINED",
    "APP",
    "DASHBOARD",
    "SETTINGS",
    "BILLING",
}

VANITY_REGEX = re.compile(r"^[A-Z0-9_-]{3,32}$")


# ---------------------------------------------------------------- Code Generation & Validation


def generate_random_suffix(length: int = 4) -> str:
    """Generates a random suffix using unambiguous Base32 characters."""
    return "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(length))


def sanitize_prefix(display_name: str, max_len: int = 6) -> str:
    """Extracts a clean uppercase alphanumeric prefix from user name."""
    clean = re.sub(r"[^A-Za-z0-9]", "", display_name).upper()
    if not clean:
        clean = "REF"
    return clean[:max_len]


def validate_vanity_code(code_str: str) -> str:
    """Validates vanity code format and checks reserved words blacklist."""
    clean = code_str.strip().upper()
    if not VANITY_REGEX.match(clean):
        raise PlatformError(
            ErrorCode.REFERRAL_CODE_INVALID,
            "Referral code must be 3-32 characters of alphanumeric, hyphens, or underscores",
        )
    if clean in RESERVED_CODES:
        raise PlatformError(
            ErrorCode.REFERRAL_CODE_FORBIDDEN,
            f"Referral code '{clean}' is a reserved keyword",
        )
    return clean


async def create_referral_code(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    code: str | None = None,
    product_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    attribution_window_days: int = 30,
    metadata_json: dict[str, Any] | None = None,
) -> ReferralCode:
    """Creates a new referral code for a partner user."""
    # Verify user exists
    user = await identity_service.get_user_by_id(session, user_id)
    if not user:
        raise PlatformError(ErrorCode.NOT_FOUND, "User not found")

    if code:
        clean_code = validate_vanity_code(code)
        # Check uniqueness
        stmt = select(ReferralCode).where(func.upper(ReferralCode.code) == clean_code)
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise PlatformError(ErrorCode.REFERRAL_CODE_TAKEN, f"Referral code '{clean_code}' is already taken")
        is_vanity = True
        final_code = clean_code
    else:
        # Default code generation with retry for uniqueness
        prefix = sanitize_prefix(user.display_name)
        is_vanity = False
        final_code = ""
        for attempt in range(10):
            suffix = generate_random_suffix(4 if attempt < 5 else 6)
            candidate = f"{prefix}{suffix}"
            stmt = select(ReferralCode).where(func.upper(ReferralCode.code) == candidate)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                final_code = candidate
                break

        if not final_code:
            final_code = f"REF{generate_random_suffix(8)}"

    entry = ReferralCode(
        user_id=user_id,
        product_id=product_id,
        campaign_id=campaign_id,
        code=final_code,
        is_vanity=is_vanity,
        status="ACTIVE",
        attribution_window_days=attribution_window_days,
        metadata_json=metadata_json or {},
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_referral_code_by_code(session: AsyncSession, code_str: str) -> ReferralCode | None:
    """Case-insensitive referral code lookup."""
    clean = code_str.strip().upper()
    stmt = select(ReferralCode).where(func.upper(ReferralCode.code) == clean)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def list_referral_codes_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[ReferralCode]:
    """Lists referral codes owned by a partner."""
    stmt = select(ReferralCode).where(ReferralCode.user_id == user_id).order_by(ReferralCode.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


# ---------------------------------------------------------------- Clicks & Attribution Token


def hash_privacy_value(val: str) -> bytes:
    """Computes SHA-256 hash for IP or User-Agent to protect user privacy."""
    return hashlib.sha256(val.encode("utf-8")).digest()


def create_attribution_token(
    *,
    click_id: uuid.UUID,
    code: str,
    product_slug: str | None = None,
    campaign: str | None = None,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Issues a signed JWS attribution token carried across domains."""
    exp_delta = expires_delta or timedelta(days=30)
    claims: dict[str, Any] = {
        "click_id": str(click_id),
        "code": code.upper(),
        "jti": str(uuid7()),
    }
    if product_slug:
        claims["product"] = product_slug
    if campaign:
        claims["campaign"] = campaign

    return create_jwt_token(claims, expires_delta=exp_delta, settings=settings)


def decode_attribution_token(token_str: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Validates and decodes signed attribution token."""
    try:
        decoded = decode_jwt_token(token_str, settings=settings)
    except PlatformError as e:
        if e.code == ErrorCode.AUTH_TOKEN_EXPIRED:
            raise PlatformError(ErrorCode.ATTRIBUTION_TOKEN_EXPIRED, "Attribution token has expired") from e
        raise PlatformError(ErrorCode.ATTRIBUTION_TOKEN_INVALID, "Invalid attribution token signature or format") from e

    if "code" not in decoded or "click_id" not in decoded:
        raise PlatformError(ErrorCode.ATTRIBUTION_TOKEN_INVALID, "Attribution token missing required claims")
    return decoded


async def record_click(
    session: AsyncSession,
    *,
    code_str: str,
    client_ip: str,
    user_agent: str,
    product_slug: str | None = None,
    referer_url: str | None = None,
    campaign: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    utm_term: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Records a referral link click and constructs redirect with signed attribution token (§7.1)."""
    code_entry = await get_referral_code_by_code(session, code_str)
    if not code_entry or code_entry.status != "ACTIVE":
        raise PlatformError(ErrorCode.REFERRAL_CODE_INVALID, f"Referral code '{code_str}' is invalid or inactive")

    # Resolve product
    target_product = None
    if product_slug:
        target_product = await catalog_service.get_product_by_slug(session, product_slug)
    elif code_entry.product_id:
        target_product = await catalog_service.get_product_by_id(session, code_entry.product_id)

    # Privacy hashing
    ip_h = hash_privacy_value(client_ip or "127.0.0.1")
    ua_h = hash_privacy_value(user_agent or "Unknown")

    click = ReferralClick(
        code_id=code_entry.id,
        product_id=target_product.id if target_product else None,
        ip_hash=ip_h,
        user_agent_hash=ua_h,
        referer_url=referer_url,
        campaign=campaign or utm_campaign,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
    )
    session.add(click)
    await session.flush()

    # Generate cross-domain attribution token
    attr_token = create_attribution_token(
        click_id=click.id,
        code=code_entry.code,
        product_slug=target_product.slug if target_product else None,
        campaign=click.campaign,
        expires_delta=timedelta(days=code_entry.attribution_window_days),
        settings=settings,
    )

    # Build target redirect URL strictly from registered signup URL (ADR 0001: no open redirect)
    redirect_url = None
    if target_product and target_product.signup_url:
        parsed = urlparse(target_product.signup_url)
        query_params = {
            "ref": code_entry.code,
            "rt": attr_token,
        }
        if utm_source:
            query_params["utm_source"] = utm_source
        if utm_medium:
            query_params["utm_medium"] = utm_medium
        if utm_campaign:
            query_params["utm_campaign"] = utm_campaign

        # Merge with existing query string if any
        if parsed.query:
            from urllib.parse import parse_qsl
            existing_params = dict(parse_qsl(parsed.query))
            existing_params.update(query_params)
            query_str = urlencode(existing_params)
        else:
            query_str = urlencode(query_params)

        redirect_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_str,
            parsed.fragment,
        ))

    return {
        "click_id": str(click.id),
        "code": code_entry.code,
        "product_id": str(target_product.id) if target_product else None,
        "product_slug": target_product.slug if target_product else None,
        "attribution_token": attr_token,
        "redirect_url": redirect_url,
    }


# ---------------------------------------------------------------- Attribution Ingestion


async def get_attribution_by_external_user(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
) -> Attribution | None:
    """Look up existing attribution for a product account."""
    stmt = select(Attribution).where(
        Attribution.product_id == product_id,
        Attribution.external_user_id == external_user_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def record_attribution(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
    registered_at: datetime,
    referral_code: str | None = None,
    attribution_token: str | None = None,
    signals: dict[str, Any] | None = None,
    attribution_grace_minutes: int = 60,
    settings: Settings | None = None,
) -> tuple[Attribution, bool]:
    """Records attribution for a new product user signup (§7.2, §7.3).

    Returns tuple of (Attribution, is_new_attribution).
    """
    clean_external_id = external_user_id.strip()

    # 1. Check idempotency on (product_id, external_user_id)
    existing = await get_attribution_by_external_user(
        session, product_id=product_id, external_user_id=clean_external_id
    )
    if existing:
        return existing, False

    # 2. Resolve code & token
    if not referral_code and not attribution_token:
        raise PlatformError(ErrorCode.REFERRAL_CODE_REQUIRED, "Either referral_code or attribution_token must be provided")

    resolved_code_str: str | None = None
    click_id: uuid.UUID | None = None

    if attribution_token:
        token_claims = decode_attribution_token(attribution_token, settings=settings)
        click_id_str = token_claims.get("click_id")
        if click_id_str:
            click_id = uuid.UUID(click_id_str)
        resolved_code_str = token_claims.get("code")

    # User-typed code takes precedence over token's code if provided
    if referral_code:
        resolved_code_str = referral_code.strip()

    if not resolved_code_str:
        raise PlatformError(ErrorCode.REFERRAL_CODE_INVALID, "No valid referral code found")

    code_entry = await get_referral_code_by_code(session, resolved_code_str)
    if not code_entry or code_entry.status != "ACTIVE":
        raise PlatformError(ErrorCode.REFERRAL_CODE_INVALID, f"Referral code '{resolved_code_str}' is invalid or inactive")

    # Product restriction check
    if code_entry.product_id and code_entry.product_id != product_id:
        raise PlatformError(
            ErrorCode.REFERRAL_CODE_FORBIDDEN,
            "This referral code is not valid for this product",
        )

    # 3. Grace period check on registered_at
    now_dt = clock.now()
    if registered_at > now_dt + timedelta(minutes=5):
        raise PlatformError(
            ErrorCode.ATTRIBUTION_TIMESTAMP_INVALID,
            "registered_at timestamp cannot be in the future",
        )
    if registered_at < now_dt - timedelta(minutes=attribution_grace_minutes):
        raise PlatformError(
            ErrorCode.ATTRIBUTION_NOT_NEW_ACCOUNT,
            f"Account registration exceeds grace window of {attribution_grace_minutes} minutes",
        )

    # 4. Self-referral prevention (§7.3.1)
    referrer_user = await identity_service.get_user_by_id(session, code_entry.user_id)
    if not referrer_user:
        raise PlatformError(ErrorCode.NOT_FOUND, "Referrer user not found")

    # Check product account link
    prod_account, _ = await catalog_service.get_or_create_product_account(
        session, product_id=product_id, external_user_id=clean_external_id
    )

    if prod_account.user_id and prod_account.user_id == referrer_user.id:
        raise PlatformError(ErrorCode.SELF_REFERRAL, "Self-referral is forbidden (same user identity)")

    # Check signal matches (email / phone against referrer)
    sig = signals or {}
    referee_email = sig.get("email")
    if referee_email and referrer_user.email:
        if referee_email.strip().lower() == referrer_user.email.strip().lower():
            raise PlatformError(ErrorCode.SELF_REFERRAL, "Self-referral is forbidden (matching email)")

    referee_phone = sig.get("phone")
    if referee_phone and referrer_user.phone:
        if referee_phone.strip() == referrer_user.phone.strip():
            raise PlatformError(ErrorCode.SELF_REFERRAL, "Self-referral is forbidden (matching phone)")

    # 5. Create Attribution
    expires_at = registered_at + timedelta(days=code_entry.attribution_window_days)
    attribution = Attribution(
        product_id=product_id,
        product_account_id=prod_account.id,
        external_user_id=clean_external_id,
        referrer_user_id=referrer_user.id,
        code_id=code_entry.id,
        click_id=click_id,
        campaign_id=code_entry.campaign_id,
        status="ATTRIBUTED",
        registered_at=registered_at,
        expires_at=expires_at,
        signals_json=sig,
    )
    session.add(attribution)
    await session.flush()

    return attribution, True


async def get_referral_metrics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> tuple[int, int, int]:
    """Returns (total_clicks, total_referrals, total_conversions)."""
    from sqlalchemy import func

    clicks_stmt = select(func.count(ReferralClick.id))
    if product_id:
        clicks_stmt = clicks_stmt.where(ReferralClick.product_id == product_id)
    total_clicks = int((await session.execute(clicks_stmt)).scalar() or 0)

    attr_stmt = select(func.count(Attribution.id))
    if product_id:
        attr_stmt = attr_stmt.where(Attribution.product_id == product_id)
    total_referrals = int((await session.execute(attr_stmt)).scalar() or 0)

    conv_stmt = select(func.count(Attribution.id)).where(Attribution.status == "CONVERTED")
    if product_id:
        conv_stmt = conv_stmt.where(Attribution.product_id == product_id)
    total_conversions = int((await session.execute(conv_stmt)).scalar() or 0)

    return total_clicks, total_referrals, total_conversions

