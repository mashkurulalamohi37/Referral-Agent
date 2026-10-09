"""Credit and subscription reservation endpoints (§11, §20)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_api_client, get_db_session
from app.catalog.models import ApiClient
from app.core.errors import ErrorCode, PlatformError
from app.credits import service as credit_service

router = APIRouter(prefix="/v1/credits", tags=["credits"])


class CreateReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_user_id: str
    currency: str = "BDT"
    requested_amount: int = Field(gt=0)
    order_ref: str
    idempotency_key: str


class CaptureReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_minor: int | None = Field(default=None, gt=0)
    payment_id: str | None = None


class RefundCreditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservation_id: uuid.UUID
    amount_minor: int = Field(gt=0)
    idempotency_key: str
    currency: str = "BDT"


@router.get("/balance")
async def get_credit_balance(
    external_user_id: Annotated[str, Query()],
    currency: Annotated[str, Query()] = "BDT",
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> dict:
    """Returns spendable credit balance for a product customer (§11)."""
    return await credit_service.get_spendable_balance(
        session,
        product_id=client.product_id,
        external_user_id=external_user_id,
        currency=currency,
    )


@router.post("/reservations")
async def create_credit_reservation(
    payload: CreateReservationRequest,
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Reserves subscription credit against user's wallet with TTL (§11)."""
    reservation, created = await credit_service.create_reservation(
        session,
        product_id=client.product_id,
        external_user_id=payload.external_user_id,
        requested_amount=payload.requested_amount,
        order_ref=payload.order_ref,
        idempotency_key=payload.idempotency_key,
        currency=payload.currency,
    )
    return {
        "reservation_id": str(reservation.id),
        "order_ref": reservation.order_ref,
        "currency": reservation.currency,
        "requested_amount": reservation.requested_minor,
        "reserved_amount": reservation.reserved_minor,
        "from_credit_only": reservation.from_credit_only_minor,
        "from_available": reservation.from_available_minor,
        "state": reservation.state,
        "expires_at": reservation.expires_at.isoformat(),
        "created": created,
    }


@router.post("/reservations/{reservation_id}/capture")
async def capture_credit_reservation(
    reservation_id: uuid.UUID,
    payload: CaptureReservationRequest,
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Captures a reserved credit (§11)."""
    reservation = await credit_service.capture_reservation(
        session,
        reservation_id=reservation_id,
        captured_minor=payload.amount_minor,
        payment_id=payload.payment_id,
    )
    return {
        "reservation_id": str(reservation.id),
        "state": reservation.state,
        "captured_amount": reservation.captured_minor,
        "late_captured_amount": reservation.late_captured_minor,
        "payment_id": reservation.payment_id,
    }


@router.post("/reservations/{reservation_id}/release")
async def release_credit_reservation(
    reservation_id: uuid.UUID,
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Releases a reserved credit (§11)."""
    reservation = await credit_service.release_reservation(
        session,
        reservation_id=reservation_id,
    )
    return {
        "reservation_id": str(reservation.id),
        "state": reservation.state,
        "reserved_amount": reservation.reserved_minor,
    }


@router.post("/refunds")
async def refund_credit(
    payload: RefundCreditRequest,
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Refunds previously captured subscription credit back to user wallet (§12)."""
    refund, created = await credit_service.refund_credit(
        session,
        product_id=client.product_id,
        reservation_id=payload.reservation_id,
        amount_minor=payload.amount_minor,
        idempotency_key=payload.idempotency_key,
        currency=payload.currency,
    )
    return {
        "refund_id": str(refund.id),
        "reservation_id": str(refund.credit_reservation_id),
        "amount_minor": refund.amount_minor,
        "currency": refund.currency,
        "created": created,
    }
