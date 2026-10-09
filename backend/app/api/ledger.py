"""Ledger and Wallet API endpoints (§10, docs/openapi.yaml)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
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
async def get_my_wallet(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    balances = await ledger_service.get_user_wallet_balances(session, current_user.id)
    return {
        "success": True,
        "data": balances,
    }
