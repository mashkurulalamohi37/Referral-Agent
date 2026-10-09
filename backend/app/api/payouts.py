"""Payout endpoints and maker-checker actions (§13, §20)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_roles
from app.core.errors import ErrorCode, PlatformError
from app.identity.models import User
from app.payouts import service as payout_service

router = APIRouter(prefix="/v1/payouts", tags=["payouts"])


class AddPayoutMethodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    details: dict[str, Any]


class RequestPayoutBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payout_method_id: uuid.UUID
    amount_minor: int = Field(gt=0)
    idempotency_key: str
    currency: str = "BDT"


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None


class RejectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


class MarkPaidBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_ref: str


@router.get("/methods")
async def list_payout_methods(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict]:
    """Lists saved payout methods for the authenticated user."""
    methods = await payout_service.get_user_payout_methods(session, user_id=user.id)
    return [
        {
            "id": str(m.id),
            "method": m.method,
            "masked_identifier": m.masked_identifier,
            "status": m.status,
            "verified_at": m.verified_at.isoformat() if m.verified_at else None,
        }
        for m in methods
    ]


@router.post("/methods")
async def add_payout_method(
    payload: AddPayoutMethodRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Saves a new payout method for the authenticated user."""
    method = await payout_service.add_payout_method(
        session,
        user_id=user.id,
        method=payload.method,
        raw_details=payload.details,
    )
    return {
        "id": str(method.id),
        "method": method.method,
        "masked_identifier": method.masked_identifier,
        "status": method.status,
    }


@router.post("/request")
async def request_payout(
    payload: RequestPayoutBody,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Submits a payout request, locking funds in Payout Hold (§13)."""
    payout, created = await payout_service.request_payout(
        session,
        user_id=user.id,
        payout_method_id=payload.payout_method_id,
        amount_minor=payload.amount_minor,
        idempotency_key=payload.idempotency_key,
        currency=payload.currency,
    )
    return {
        "payout_id": str(payout.id),
        "currency": payout.currency,
        "amount_minor": payout.amount_minor,
        "tax_withheld_minor": payout.tax_withheld_minor,
        "net_minor": payout.net_minor,
        "state": payout.state,
        "needs_review": payout.needs_review,
        "created": created,
    }


@router.post("/{payout_id}/approve")
async def approve_payout(
    payout_id: uuid.UUID,
    payload: DecisionBody,
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "FINANCE_ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Maker-checker approval for a payout (§13)."""
    payout = await payout_service.approve_payout(
        session,
        payout_id=payout_id,
        actor_id=admin_user.id,
        note=payload.note,
    )
    return {
        "payout_id": str(payout.id),
        "state": payout.state,
    }


@router.post("/{payout_id}/reject")
async def reject_payout(
    payout_id: uuid.UUID,
    payload: RejectBody,
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "FINANCE_ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Rejects a payout and returns locked funds to user available balance (§13)."""
    payout = await payout_service.reject_payout(
        session,
        payout_id=payout_id,
        actor_id=admin_user.id,
        reason=payload.reason,
    )
    return {
        "payout_id": str(payout.id),
        "state": payout.state,
    }


@router.post("/{payout_id}/mark-paid")
async def mark_payout_paid(
    payout_id: uuid.UUID,
    payload: MarkPaidBody,
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "FINANCE_ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Marks an approved payout as PAID and settles ledger clearing (§13)."""
    payout = await payout_service.mark_payout_paid(
        session,
        payout_id=payout_id,
        provider_ref=payload.provider_ref,
    )
    return {
        "payout_id": str(payout.id),
        "state": payout.state,
        "provider_ref": payout.provider_ref,
    }


@router.get("/export/csv")
async def export_payouts_csv(
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "FINANCE_ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    currency: str = "BDT",
) -> Response:
    """Exports approved payouts to CSV format."""
    csv_data = await payout_service.export_payouts_csv(session, currency=currency)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=payouts.csv"})
