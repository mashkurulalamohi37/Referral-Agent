"""Commissions and Rules API endpoints (§9, docs/openapi.yaml)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_db_session,
    require_roles,
)
from app.commissions import service as commission_service
from app.commissions.models import Commission, CommissionRule
from app.core.errors import ErrorCode, PlatformError
from app.identity.models import User

router = APIRouter(tags=["commissions"])


# ---------------------------------------------------------------- Schemas


class CreateRuleRequest(BaseModel):
    rule_name: str = Field(min_length=1, max_length=128)
    product_id: uuid.UUID | None = None
    plan_code: str | None = None
    partner_type: str | None = None
    partner_id: uuid.UUID | None = None
    campaign_id: uuid.UUID | None = None
    billing_reason: str | None = None
    commission_type: str = "PERCENTAGE"
    rate_bps: int = Field(default=1000, ge=0, le=10000)
    fixed_amount_minor: int = Field(default=0, ge=0)
    currency: str = "BDT"
    min_net_paid_minor: int = 0
    max_commission_minor: int | None = None
    eligible_months_from_conversion: int = 12
    max_payments_per_referral: int | None = None
    reward_split: dict[str, Any] = Field(default_factory=lambda: {"WALLET": 100})
    confirmation_days: int = Field(default=14, ge=0)
    priority: int = 0


# ---------------------------------------------------------------- Partner Commissions


@router.get(
    "/v1/commissions",
    response_model=dict[str, Any],
    summary="List current partner's earned commissions",
)
async def list_commissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    stmt = (
        select(Commission)
        .where(Commission.referrer_user_id == current_user.id)
        .order_by(Commission.earned_at.desc())
    )
    res = await session.execute(stmt)
    commissions = list(res.scalars().all())

    return {
        "success": True,
        "data": [
            {
                "id": str(c.id),
                "product_id": str(c.product_id),
                "payment_id": c.payment_id,
                "amount_minor": c.amount_minor,
                "currency": c.currency,
                "status": c.status,
                "earned_at": c.earned_at.isoformat(),
                "confirmation_due_at": c.confirmation_due_at.isoformat(),
                "confirmed_at": c.confirmed_at.isoformat() if c.confirmed_at else None,
            }
            for c in commissions
        ],
    }


# ---------------------------------------------------------------- Admin Rules


@router.post(
    "/v1/admin/rules",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Create commission rule",
)
async def create_rule_endpoint(
    payload: CreateRuleRequest,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    rule = await commission_service.create_commission_rule(
        session,
        rule_name=payload.rule_name,
        product_id=payload.product_id,
        plan_code=payload.plan_code,
        partner_type=payload.partner_type,
        partner_id=payload.partner_id,
        campaign_id=payload.campaign_id,
        billing_reason=payload.billing_reason,
        commission_type=payload.commission_type,
        rate_bps=payload.rate_bps,
        fixed_amount_minor=payload.fixed_amount_minor,
        currency=payload.currency,
        min_net_paid_minor=payload.min_net_paid_minor,
        max_commission_minor=payload.max_commission_minor,
        eligible_months_from_conversion=payload.eligible_months_from_conversion,
        max_payments_per_referral=payload.max_payments_per_referral,
        reward_split=payload.reward_split,
        confirmation_days=payload.confirmation_days,
        priority=payload.priority,
    )
    return {
        "success": True,
        "data": {
            "id": str(rule.id),
            "rule_name": rule.rule_name,
            "commission_type": rule.commission_type,
            "rate_bps": rule.rate_bps,
            "fixed_amount_minor": rule.fixed_amount_minor,
            "confirmation_days": rule.confirmation_days,
            "status": rule.status,
        },
    }
