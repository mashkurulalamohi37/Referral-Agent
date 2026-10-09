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
