"""Ledger and Wallet API endpoints (§10, docs/openapi.yaml)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_db_session,
)
from app.identity.models import User
from app.ledger import service as ledger_service

router = APIRouter(tags=["ledger"])


@router.get(
    "/v1/wallet/me",
    response_model=dict[str, Any],
    summary="Get current partner's multi-bucket wallet balance (§10.1)",
)
@router.get(
    "/v1/me/wallet",
    response_model=dict[str, Any],
    summary="Get current partner's multi-bucket wallet balance (§10.5, docs/openapi.yaml)",
)
async def get_my_wallet(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    balances = await ledger_service.get_user_wallet_balances(session, current_user.id)
    return {
        "success": True,
        "data": balances,
    }


@router.get(
    "/v1/me/wallet/transactions",
    response_model=dict[str, Any],
    summary="List ledger-backed statement history (§10.5, docs/openapi.yaml)",
)
@router.get(
    "/v1/wallet/transactions",
    response_model=dict[str, Any],
    summary="List wallet transactions",
)
async def get_my_wallet_transactions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    currency: str = Query(default="BDT", max_length=3),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    txs = await ledger_service.list_wallet_transactions(
        session,
        user_id=current_user.id,
        currency=currency,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(tx.id),
                "transaction_type": tx.transaction_type,
                "reference_type": tx.reference_type,
                "reference_id": tx.reference_id,
                "description": tx.description,
                "posted_at": tx.posted_at.isoformat(),
            }
            for tx in txs
        ],
    }
