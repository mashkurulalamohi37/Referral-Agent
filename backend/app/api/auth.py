"""Auth API endpoints (§20: login, refresh, logout, handoff)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_api_client, get_db_session, require_api_scopes
from app.catalog.models import ApiClient
from app.core.errors import ErrorCode, PlatformError
from app.identity import service as identity_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class HandoffRequest(BaseModel):
    product_id: uuid.UUID
    external_user_id: str


class HandoffExchangeRequest(BaseModel):
    handoff_token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Registers a new partner account, generates default referral code, and returns JWT tokens."""
    clean_email = str(body.email).lower().strip()
    existing = await identity_service.get_user_by_email(session, clean_email)
    if existing:
        raise PlatformError(
            ErrorCode.CONFLICT,
            f"An account with email '{clean_email}' already exists",
        )

    user = await identity_service.create_user(
        session,
        display_name=body.display_name.strip(),
        email=clean_email,
        password=body.password,
        phone=body.phone,
        roles=["PARTNER", "CUSTOMER"],
    )

    try:
        from app.referrals import service as referrals_service
        await referrals_service.create_referral_code(session, user_id=user.id)
    except Exception:
        pass

    tokens = await identity_service.issue_auth_tokens(
        session, user=user, settings=request.app.state.settings
    )
    return {"success": True, "data": tokens}


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Authenticates user with email & password, returning JWT access & refresh tokens."""
    user = await identity_service.authenticate_user_password(
        session, email=str(body.email), password=body.password
    )
    tokens = await identity_service.issue_auth_tokens(
        session, user=user, settings=request.app.state.settings
    )
    return {"success": True, "data": tokens}


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Rotates refresh token and returns new access & refresh token pair."""
    tokens = await identity_service.rotate_refresh_token(
        session, refresh_token=body.refresh_token, settings=request.app.state.settings
    )
    return {"success": True, "data": tokens}


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Revokes refresh token."""
    await identity_service.revoke_refresh_token(session, refresh_token=body.refresh_token)
    return {"success": True, "data": {"message": "Logged out successfully"}}


@router.post("/handoff")
async def create_handoff(
    body: HandoffRequest,
    client: Annotated[ApiClient, Depends(require_api_scopes("auth:handoff"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Issues a short-lived (60s) single-use handoff token for seamless product SSO."""
    token = await identity_service.create_handoff_token(
        session, product_id=body.product_id, external_user_id=body.external_user_id
    )
    return {"success": True, "data": {"handoff_token": token, "expires_in": 60}}


@router.post("/handoff/exchange")
async def exchange_handoff(
    body: HandoffExchangeRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Exchanges a single-use handoff token for JWT access + refresh tokens."""
    tokens = await identity_service.exchange_handoff_token(
        session, handoff_token=body.handoff_token, settings=request.app.state.settings
    )
    return {"success": True, "data": tokens}
