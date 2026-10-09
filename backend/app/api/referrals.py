"""Referrals and Attribution API endpoints (§6, §7, docs/openapi.yaml)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    authenticate_api_client_dep,
    get_current_active_user,
    get_db_session,
    require_roles,
)
from app.catalog.models import ApiClient
from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.identity.models import User
from app.referrals import service as referral_service

router = APIRouter(tags=["referrals"])


# ---------------------------------------------------------------- Schemas


class CreateReferralCodeRequest(BaseModel):
    code: str | None = Field(default=None, max_length=32, description="Optional vanity code")
    product_id: uuid.UUID | None = Field(default=None, description="Optional product restriction")
    attribution_window_days: int = Field(default=30, ge=1, le=365)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReferralCodeResponse(BaseModel):
    id: uuid.UUID
    code: str
    user_id: uuid.UUID
    product_id: uuid.UUID | None
    is_vanity: bool
    status: str
    attribution_window_days: int
    created_at: datetime


class PublicCodeResponse(BaseModel):
    code: str
    valid: bool
    referrer_name: str | None = None


class AttributionRequest(BaseModel):
    external_user_id: str = Field(min_length=1, max_length=255)
    registered_at: datetime
    referral_code: str | None = None
    attribution_token: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)


class AttributionResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    external_user_id: str
    referrer_user_id: uuid.UUID
    code_id: uuid.UUID
    status: str
    registered_at: datetime
    expires_at: datetime
    is_new: bool


# ---------------------------------------------------------------- Partner Code Management


@router.post(
    "/v1/referrals/codes",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new referral code",
)
async def create_referral_code(
    payload: CreateReferralCodeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    code_entry = await referral_service.create_referral_code(
        session,
        user_id=current_user.id,
        code=payload.code,
        product_id=payload.product_id,
        attribution_window_days=payload.attribution_window_days,
        metadata_json=payload.metadata,
    )
    return {
        "success": True,
        "data": {
            "id": str(code_entry.id),
            "code": code_entry.code,
            "user_id": str(code_entry.user_id),
            "product_id": str(code_entry.product_id) if code_entry.product_id else None,
            "is_vanity": code_entry.is_vanity,
            "status": code_entry.status,
            "attribution_window_days": code_entry.attribution_window_days,
            "created_at": code_entry.created_at.isoformat(),
        },
    }


@router.get(
    "/v1/referrals/codes",
    response_model=dict[str, Any],
    summary="List current partner's referral codes",
)
async def list_referral_codes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    codes = await referral_service.list_referral_codes_for_user(session, current_user.id)
    return {
        "success": True,
        "data": [
            {
                "id": str(c.id),
                "code": c.code,
                "product_id": str(c.product_id) if c.product_id else None,
                "is_vanity": c.is_vanity,
                "status": c.status,
                "attribution_window_days": c.attribution_window_days,
                "created_at": c.created_at.isoformat(),
            }
            for c in codes
        ],
    }


# ---------------------------------------------------------------- Public Code Validation & Click Redirect


@router.get(
    "/v1/public/codes/{code}",
    response_model=dict[str, Any],
    summary="Validate referral code and return minimal info against enumeration",
)
async def validate_public_code(
    code: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    code_entry = await referral_service.get_referral_code_by_code(session, code)
    if not code_entry or code_entry.status != "ACTIVE":
        return {
            "success": True,
            "data": {
                "code": code.upper(),
                "valid": False,
                "referrer_name": None,
            },
        }

    from app.identity import service as identity_service

    referrer = await identity_service.get_user_by_id(session, code_entry.user_id)
    return {
        "success": True,
        "data": {
            "code": code_entry.code,
            "valid": True,
            "referrer_name": referrer.display_name if referrer else None,
        },
    }


@router.get(
    "/r/{code}",
    summary="Cross-domain click redirect handler (§7.1)",
)
async def handle_referral_click(
    code: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    product: str | None = Query(default=None, description="Product slug"),
    campaign: str | None = Query(default=None),
    utm_source: str | None = Query(default=None),
    utm_medium: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
    utm_content: str | None = Query(default=None),
    utm_term: str | None = Query(default=None),
) -> Response:
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer")

    click_result = await referral_service.record_click(
        session,
        code_str=code,
        client_ip=client_ip,
        user_agent=user_agent,
        product_slug=product,
        referer_url=referer,
        campaign=campaign,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        settings=settings,
    )

    if click_result.get("redirect_url"):
        return RedirectResponse(
            url=click_result["redirect_url"],
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # If generic code without specific product, return click details
    return Response(
        content=f'{{"success": true, "data": {click_result}}}',
        media_type="application/json",
    )


# ---------------------------------------------------------------- Product Attribution Intake


@router.post(
    "/v1/attributions",
    response_model=dict[str, Any],
    summary="Record product user attribution (§7.2, §7.3)",
)
async def record_attribution_endpoint(
    payload: AttributionRequest,
    api_client: Annotated[ApiClient, Depends(authenticate_api_client_dep)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    # Product is strictly derived from API Client credential (ADR 0001, §5.5)
    attribution, is_new = await referral_service.record_attribution(
        session,
        product_id=api_client.product_id,
        external_user_id=payload.external_user_id,
        registered_at=payload.registered_at,
        referral_code=payload.referral_code,
        attribution_token=payload.attribution_token,
        signals=payload.signals,
        settings=settings,
    )

    return {
        "success": True,
        "data": {
            "id": str(attribution.id),
            "product_id": str(attribution.product_id),
            "external_user_id": attribution.external_user_id,
            "referrer_user_id": str(attribution.referrer_user_id),
            "code_id": str(attribution.code_id),
            "status": attribution.status,
            "registered_at": attribution.registered_at.isoformat(),
            "expires_at": attribution.expires_at.isoformat(),
            "is_new": is_new,
        },
    }
