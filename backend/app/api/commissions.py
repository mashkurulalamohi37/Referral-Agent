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
    tier_schedule: dict[str, Any] | None = None
    currency: str = "BDT"
    min_net_paid_minor: int = 0
    max_commission_minor: int | None = None
    eligible_months_from_conversion: int = 12
    max_payments_per_referral: int | None = None
    reward_split: dict[str, Any] = Field(default_factory=lambda: {"WALLET": 100})
    confirmation_days: int = Field(default=14, ge=0)
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    rule_name: str | None = None
    commission_type: str | None = None
    rate_bps: int | None = Field(default=None, ge=0, le=10000)
    fixed_amount_minor: int | None = Field(default=None, ge=0)
    tier_schedule: dict[str, Any] | None = None
    status: str | None = None
    priority: int | None = None
    confirmation_days: int | None = Field(default=None, ge=0)
    partner_type: str | None = None
    min_net_paid_minor: int | None = None
    max_commission_minor: int | None = None


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


# ---------------------------------------------------------------- Admin Dynamic Rules CRUD


@router.get(
    "/v1/admin/rules",
    response_model=dict[str, Any],
    summary="Admin: List all commission rules dynamically",
)
async def list_rules_endpoint(
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: uuid.UUID | None = Query(default=None),
    partner_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    rules = await commission_service.list_commission_rules(
        session,
        product_id=product_id,
        partner_type=partner_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "rule_name": r.rule_name,
                "product_id": str(r.product_id) if r.product_id else None,
                "partner_type": r.partner_type,
                "commission_type": r.commission_type,
                "rate_bps": r.rate_bps,
                "fixed_amount_minor": r.fixed_amount_minor,
                "tier_schedule": r.tier_schedule,
                "currency": r.currency,
                "confirmation_days": r.confirmation_days,
                "priority": r.priority,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rules
        ],
    }


@router.get(
    "/v1/admin/rules/{rule_id}",
    response_model=dict[str, Any],
    summary="Admin: Get single commission rule",
)
async def get_rule_endpoint(
    rule_id: uuid.UUID,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    rule = await commission_service.get_commission_rule_by_id(session, rule_id)
    if not rule:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Commission rule '{rule_id}' not found")
    return {
        "success": True,
        "data": {
            "id": str(rule.id),
            "rule_name": rule.rule_name,
            "product_id": str(rule.product_id) if rule.product_id else None,
            "plan_code": rule.plan_code,
            "partner_type": rule.partner_type,
            "commission_type": rule.commission_type,
            "rate_bps": rule.rate_bps,
            "fixed_amount_minor": rule.fixed_amount_minor,
            "tier_schedule": rule.tier_schedule,
            "currency": rule.currency,
            "min_net_paid_minor": rule.min_net_paid_minor,
            "max_commission_minor": rule.max_commission_minor,
            "confirmation_days": rule.confirmation_days,
            "priority": rule.priority,
            "status": rule.status,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat(),
        },
    }


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
        tier_schedule=payload.tier_schedule,
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
            "tier_schedule": rule.tier_schedule,
            "confirmation_days": rule.confirmation_days,
            "status": rule.status,
        },
    }


@router.patch(
    "/v1/admin/rules/{rule_id}",
    response_model=dict[str, Any],
    summary="Admin: Update dynamic commission rule",
)
async def update_rule_endpoint(
    rule_id: uuid.UUID,
    payload: UpdateRuleRequest,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    rule = await commission_service.update_commission_rule(
        session,
        rule_id,
        rule_name=payload.rule_name,
        rate_bps=payload.rate_bps,
        fixed_amount_minor=payload.fixed_amount_minor,
        commission_type=payload.commission_type,
        tier_schedule=payload.tier_schedule,
        status=payload.status,
        priority=payload.priority,
        confirmation_days=payload.confirmation_days,
        partner_type=payload.partner_type,
        min_net_paid_minor=payload.min_net_paid_minor,
        max_commission_minor=payload.max_commission_minor,
    )
    return {
        "success": True,
        "data": {
            "id": str(rule.id),
            "rule_name": rule.rule_name,
            "commission_type": rule.commission_type,
            "rate_bps": rule.rate_bps,
            "fixed_amount_minor": rule.fixed_amount_minor,
            "tier_schedule": rule.tier_schedule,
            "confirmation_days": rule.confirmation_days,
            "status": rule.status,
        },
    }


@router.delete(
    "/v1/admin/rules/{rule_id}",
    response_model=dict[str, Any],
    summary="Admin: Deactivate / Archive commission rule",
)
async def delete_rule_endpoint(
    rule_id: uuid.UUID,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    await commission_service.delete_commission_rule(session, rule_id)
    return {"success": True, "message": f"Rule {rule_id} archived successfully"}


class SimulateRuleRequest(BaseModel):
    product_slug: str | None = None
    plan_code: str | None = None
    partner_type: str | None = None
    billing_reason: str = "initial"
    amount_net_paid: int = Field(gt=0, description="Amount net paid in minor units (poisha)")
    sale_count: int = Field(default=1, ge=1, description="Cumulative sale count for progressive tier evaluation")
    currency: str = "BDT"


@router.post(
    "/v1/admin/commission-rules/simulate",
    response_model=dict[str, Any],
    summary="Admin: Simulate rule resolution and commission calculation (§17.1)",
)
async def simulate_commission_rule(
    payload: SimulateRuleRequest,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    from app.catalog import service as catalog_service
    product_id = None
    if payload.product_slug:
        product = await catalog_service.get_product_by_slug(session, payload.product_slug)
        if product:
            product_id = product.id

    rule = await commission_service.resolve_commission_rule(
        session,
        product_id=product_id,
        plan_code=payload.plan_code,
        partner_type=payload.partner_type,
        billing_reason=payload.billing_reason,
        currency=payload.currency,
        paid_at=clock.now(),
    )

    if not rule:
        return {
            "success": True,
            "data": {
                "matched": False,
                "rule_name": "GLOBAL_DEFAULT_OR_NONE",
                "commission_amount_minor": 0,
                "rate_bps": 0,
                "specificity_score": 0,
                "reward_split": {"WALLET": 100},
            },
        }

    score = commission_service.calculate_rule_specificity_score(
        rule,
        has_partner_type_match=bool(payload.partner_type and rule.partner_type == payload.partner_type),
        has_plan_match=bool(payload.plan_code and rule.plan_code == payload.plan_code),
        has_billing_match=bool(rule.billing_reason and rule.billing_reason == payload.billing_reason),
        has_product_match=bool(product_id and rule.product_id == product_id),
    )
    comm_amount = commission_service.calculate_commission_amount(payload.amount_net_paid, rule, sale_count=payload.sale_count)

    return {
        "success": True,
        "data": {
            "matched": True,
            "rule_id": str(rule.id),
            "rule_name": rule.rule_name,
            "commission_type": rule.commission_type,
            "rate_bps": rule.rate_bps,
            "specificity_score": score,
            "sale_count": payload.sale_count,
            "commission_amount_minor": comm_amount,
            "tier_schedule": rule.tier_schedule,
            "reward_split": rule.reward_split,
            "confirmation_days": rule.confirmation_days,
        },
    }
