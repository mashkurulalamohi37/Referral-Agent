"""Identity public service interface (§3 module boundaries, §21, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.core.ids import uuid7
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.identity.models import AuthHandoffToken, RefreshToken, User, UserRole

ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=30)
HANDOFF_TOKEN_EXPIRE = timedelta(seconds=60)

# ---------------------------------------------------------------- Users & Roles


async def create_user(
    session: AsyncSession,
    *,
    display_name: str,
    email: str | None = None,
    phone: str | None = None,
    password: str | None = None,
    locale: str = "en",
    time_zone: str = "Asia/Dhaka",
    roles: list[str] | None = None,
) -> User:
    """Creates a user and assigns default or specified roles."""
    clean_email = email.lower().strip() if email else None
    if clean_email:
        existing = await get_user_by_email(session, clean_email)
        if existing:
            raise PlatformError(ErrorCode.CONFLICT, f"User with email '{clean_email}' already exists")

    pw_hash = hash_password(password) if password else None
    user = User(
        display_name=display_name.strip(),
        email=clean_email,
        email_verified=False,
        phone=phone.strip() if phone else None,
        phone_verified=False,
        password_hash=pw_hash,
        locale=locale,
        time_zone=time_zone,
        status="ACTIVE",
        kyc_status="NONE",
    )
    session.add(user)
    await session.flush()

    assigned_roles = roles or ["CUSTOMER"]
    for role_name in assigned_roles:
        session.add(UserRole(user_id=user.id, role=role_name))
    await session.flush()
    await session.refresh(user, ["roles"])

    return user


async def get_user_roles(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Fetches list of role names for a user."""
    stmt = select(UserRole.role).where(UserRole.user_id == user_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetches active user by UUID."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetches user by email (case-insensitive)."""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(User)
        .options(selectinload(User.roles))
        .where(func.lower(User.email) == email.lower().strip(), User.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def assign_role(session: AsyncSession, *, user_id: uuid.UUID, role: str, granted_by: uuid.UUID | None = None) -> None:
    """Assigns a role to a user if not already granted."""
    stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role == role)
    result = await session.execute(stmt)
    if not result.scalar_one_or_none():
        session.add(UserRole(user_id=user_id, role=role, granted_by=granted_by))
        await session.flush()


# ---------------------------------------------------------------- Authentication & Tokens


async def authenticate_user_password(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    """Authenticates a user by email and plain password."""
    user = await get_user_by_email(session, email)
    if not user or not user.password_hash:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid email or password")
    if user.status != "ACTIVE":
        raise PlatformError(ErrorCode.PERMISSION_DENIED, f"Account is {user.status.lower()}")
    if not verify_password(password, user.password_hash):
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid email or password")
    return user


async def issue_auth_tokens(
    session: AsyncSession,
    *,
    user: User,
    family_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Issues a new JWT access token and a refresh token (with family tracking)."""
    roles = await get_user_roles(session, user.id)
    access_token = create_jwt_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "roles": roles,
            "jti": str(uuid7()),
        },
        expires_delta=ACCESS_TOKEN_EXPIRE,
        settings=settings,
    )

    fam_id = family_id or uuid7()
    plain_refresh = generate_secure_token(48)
    token_h = hash_token(plain_refresh)
    now_dt = clock.now()

    refresh_entry = RefreshToken(
        user_id=user.id,
        family_id=fam_id,
        token_hash=token_h,
        expires_at=now_dt + REFRESH_TOKEN_EXPIRE,
    )
    session.add(refresh_entry)
    await session.flush()

    return {
        "access_token": access_token,
        "refresh_token": plain_refresh,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds()),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "roles": roles,
        },
    }


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    refresh_token: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Rotates a refresh token.

    Security rule: if a previously revoked/rotated token is reused, revoke the ENTIRE family!
    """
    token_h = hash_token(refresh_token.strip())
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_h)
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid refresh token")

    # If the token was already revoked, someone is reusing an old token -> breach alert -> revoke entire family!
    if entry.revoked_at is not None:
        fam_stmt = select(RefreshToken).where(
            RefreshToken.family_id == entry.family_id,
            RefreshToken.revoked_at.is_(None),
        )
        fam_res = await session.execute(fam_stmt)
        for t in fam_res.scalars().all():
            t.revoked_at = clock.now()
            t.revoke_reason = "REUSE_DETECTED"
        await session.flush()
        raise PlatformError(
            ErrorCode.AUTH_REFRESH_REUSED, "Refresh token reuse detected; all family sessions invalidated"
        )

    now_dt = clock.now()
    if entry.expires_at < now_dt:
        entry.revoked_at = now_dt
        entry.revoke_reason = "EXPIRED"
        await session.flush()
        raise PlatformError(ErrorCode.AUTH_TOKEN_EXPIRED, "Refresh token has expired")

    user = await get_user_by_id(session, entry.user_id)
    if not user or user.status != "ACTIVE":
        raise PlatformError(ErrorCode.PERMISSION_DENIED, "User account is inactive")

    # Mark current token as rotated
    entry.revoked_at = now_dt
    entry.revoke_reason = "ROTATED"

    # Issue new token pair preserving family_id
    new_plain_refresh = generate_secure_token(48)
    new_token_h = hash_token(new_plain_refresh)
    new_refresh = RefreshToken(
        user_id=user.id,
        family_id=entry.family_id,
        token_hash=new_token_h,
        expires_at=now_dt + REFRESH_TOKEN_EXPIRE,
    )
    session.add(new_refresh)
    await session.flush()

    entry.replaced_by = new_refresh.id
    await session.flush()

    roles = await get_user_roles(session, user.id)
    access_token = create_jwt_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "roles": roles,
            "jti": str(uuid7()),
        },
        expires_delta=ACCESS_TOKEN_EXPIRE,
        settings=settings,
    )

    return {
        "access_token": access_token,
        "refresh_token": new_plain_refresh,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds()),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "roles": roles,
        },
    }


async def revoke_refresh_token(session: AsyncSession, *, refresh_token: str) -> None:
    """Revokes a refresh token on logout."""
    token_h = hash_token(refresh_token.strip())
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_h)
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry and entry.revoked_at is None:
        entry.revoked_at = clock.now()
        entry.revoke_reason = "LOGOUT"
        await session.flush()


# ---------------------------------------------------------------- SSO Handoff Tokens


async def create_handoff_token(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
) -> str:
    """Issues a short-lived (60s) single-use SSO handoff token for a product account."""
    account = await catalog_service.get_product_account(
        session, product_id=product_id, external_user_id=external_user_id
    )
    if not account:
        raise PlatformError(ErrorCode.NOT_FOUND, "Product account not found")

    plain_token = f"hnd_{generate_secure_token(32)}"
    token_h = hash_token(plain_token)
    now_dt = clock.now()

    handoff = AuthHandoffToken(
        token_hash=token_h,
        product_id=product_id,
        product_account_id=account.id,
        expires_at=now_dt + HANDOFF_TOKEN_EXPIRE,
    )
    session.add(handoff)
    await session.flush()
    return plain_token


async def exchange_handoff_token(
    session: AsyncSession,
    *,
    handoff_token: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Exchanges a single-use handoff token for JWT access + refresh tokens."""
    token_h = hash_token(handoff_token.strip())
    stmt = select(AuthHandoffToken).where(AuthHandoffToken.token_hash == token_h)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise PlatformError(ErrorCode.AUTH_HANDOFF_INVALID, "Invalid handoff token")
    if record.consumed_at is not None:
        raise PlatformError(ErrorCode.AUTH_HANDOFF_INVALID, "Handoff token has already been consumed")
    if record.expires_at < clock.now():
        raise PlatformError(ErrorCode.AUTH_HANDOFF_INVALID, "Handoff token has expired")

    # Consume single-use token
    record.consumed_at = clock.now()
    await session.flush()

    # Look up product account
    account = await catalog_service.get_product_account_by_id(session, record.product_account_id)
    if not account:
        raise PlatformError(ErrorCode.NOT_FOUND, "Product account not found")

    user: User | None = None
    if account.user_id:
        user = await get_user_by_id(session, account.user_id)

    if not user:
        # Create user for this product account if unlinked
        user = await create_user(
            session,
            display_name=f"User {account.external_user_id}",
            roles=["CUSTOMER", "PARTNER"],
        )
        account.user_id = user.id
        await session.flush()

    return await issue_auth_tokens(session, user=user, settings=settings)



# ---------------------------------------------------------------- Referrer Enrollment


async def enroll_referrer(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
    display_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    account_metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Enrolls an external product user as a referrer on the platform (§1, §20)."""
    # 1. Get or create product account
    account, is_new_account = await catalog_service.get_or_create_product_account(
        session,
        product_id=product_id,
        external_user_id=external_user_id,
        account_metadata=account_metadata,
    )

    user: User | None = None
    if account.user_id:
        user = await get_user_by_id(session, account.user_id)

    if not user and email:
        user = await get_user_by_email(session, email)

    if not user:
        name = display_name or f"User {external_user_id}"
        user = await create_user(
            session,
            display_name=name,
            email=email,
            phone=phone,
            roles=["PARTNER", "CUSTOMER"],
        )
        account.user_id = user.id
        await session.flush()
    else:
        await assign_role(session, user_id=user.id, role="PARTNER")
        if not account.user_id:
            account.user_id = user.id
            await session.flush()

    # Fetch user roles
    roles_stmt = select(UserRole.role).where(UserRole.user_id == user.id)
    roles_res = await session.execute(roles_stmt)
    user_roles = list(roles_res.scalars().all())

    return {
        "user_id": str(user.id),
        "product_account_id": str(account.id),
        "product_id": str(product_id),
        "external_user_id": account.external_user_id,
        "display_name": user.display_name,
        "email": user.email,
        "roles": user_roles,
        "is_new_account": is_new_account,
    }
