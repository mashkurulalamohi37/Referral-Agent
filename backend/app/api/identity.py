"""Identity API endpoints (§20: /me, /referrers/enroll)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_api_scopes
from app.catalog.models import ApiClient
from app.identity import service as identity_service
from app.identity.models import User

router = APIRouter(tags=["identity"])


class EnrollReferrerRequest(BaseModel):
    product_id: uuid.UUID
    external_user_id: str
    display_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    metadata: dict[str, Any] | None = None


@router.get("/me")
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Returns profile and roles for the currently authenticated user."""
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "phone": user.phone,
            "agent_type": user.agent_type,
            "company_name": user.company_name,
            "trade_license_number": user.trade_license_number,
            "tax_identification_number": user.tax_identification_number,
            "representative_designation": user.representative_designation,
            "locale": user.locale,
            "time_zone": user.time_zone,
            "status": user.status,
            "kyc_status": user.kyc_status,
            "roles": [r.role for r in user.roles],
            "created_at": user.created_at.isoformat(),
        },
    }


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    agent_type: str | None = None
    company_name: str | None = None
    trade_license_number: str | None = None
    tax_identification_number: str | None = None
    representative_designation: str | None = None
    phone: str | None = None


@router.patch("/me")
async def update_me(
    body: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Updates profile, agent classification, or company details for the current user."""
    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    if body.agent_type is not None:
        if body.agent_type.upper() in ("INDIVIDUAL", "COMPANY"):
            user.agent_type = body.agent_type.upper()
    if body.company_name is not None:
        user.company_name = body.company_name.strip() if body.company_name else None
    if body.trade_license_number is not None:
        user.trade_license_number = body.trade_license_number.strip() if body.trade_license_number else None
    if body.tax_identification_number is not None:
        user.tax_identification_number = body.tax_identification_number.strip() if body.tax_identification_number else None
    if body.representative_designation is not None:
        user.representative_designation = body.representative_designation.strip() if body.representative_designation else None
    if body.phone is not None:
        user.phone = body.phone.strip() if body.phone else None

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "phone": user.phone,
            "agent_type": user.agent_type,
            "company_name": user.company_name,
            "trade_license_number": user.trade_license_number,
            "tax_identification_number": user.tax_identification_number,
            "representative_designation": user.representative_designation,
            "locale": user.locale,
            "time_zone": user.time_zone,
            "status": user.status,
            "kyc_status": user.kyc_status,
            "roles": [r.role for r in user.roles],
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post("/referrers/enroll")
async def enroll_referrer(
    body: EnrollReferrerRequest,
    client: Annotated[ApiClient, Depends(require_api_scopes("referrers:enroll"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Enrolls an external product account as a platform referrer (§1, §20)."""
    result = await identity_service.enroll_referrer(
        session,
        product_id=body.product_id,
        external_user_id=body.external_user_id,
        display_name=body.display_name,
        email=str(body.email) if body.email else None,
        phone=body.phone,
        account_metadata=body.metadata,
    )
    return {"success": True, "data": result}
