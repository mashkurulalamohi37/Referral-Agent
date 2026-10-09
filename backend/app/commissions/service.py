"""Commission calculation and lifecycle public service (§9, ADR 0022)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.commissions.models import Commission, CommissionRule
from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.ledger import service as ledger_service
from app.referrals import service as referral_service


# ---------------------------------------------------------------- Specificity Scoring (ADR 0022)


def calculate_rule_specificity_score(
    rule: CommissionRule,
    *,
    has_partner_match: bool = False,
    has_campaign_match: bool = False,
    has_partner_type_match: bool = False,
    has_plan_match: bool = False,
    has_billing_match: bool = False,
    has_product_match: bool = False,
) -> int:
    """Calculates deterministic specificity score bitmask (ADR 0022, §9.2)."""
    score = 0
    if rule.partner_id and has_partner_match:
        score += 128
    if rule.campaign_id and has_campaign_match:
        score += 64
    if rule.partner_type and has_partner_type_match:
        score += 32
    if rule.plan_code and has_plan_match:
        score += 16
    if rule.billing_reason and has_billing_match:
        score += 8
    if rule.product_id and has_product_match:
        score += 4
    score += rule.priority
    return score


# ---------------------------------------------------------------- Rules Management & Resolution


async def create_commission_rule(
    session: AsyncSession,
    *,
    rule_name: str,
    product_id: uuid.UUID | None = None,
    plan_code: str | None = None,
    partner_type: str | None = None,
    partner_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    billing_reason: str | None = None,
    commission_type: str = "PERCENTAGE",
    rate_bps: int = 1000,
    fixed_amount_minor: int = 0,
    tier_schedule: dict[str, Any] | None = None,
    currency: str = "BDT",
    min_net_paid_minor: int = 0,
    max_commission_minor: int | None = None,
    eligible_months_from_conversion: int = 12,
    max_payments_per_referral: int | None = None,
    reward_split: dict[str, Any] | None = None,
    confirmation_days: int = 14,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
    priority: int = 0,
) -> CommissionRule:
    """Creates a versioned commission rule."""
    rule = CommissionRule(
        rule_name=rule_name,
        product_id=product_id,
        plan_code=plan_code,
        partner_type=partner_type,
        partner_id=partner_id,
        campaign_id=campaign_id,
        billing_reason=billing_reason,
        commission_type=commission_type,
        rate_bps=rate_bps,
        fixed_amount_minor=fixed_amount_minor,
        tier_schedule=tier_schedule,
        currency=currency,
        min_net_paid_minor=min_net_paid_minor,
        max_commission_minor=max_commission_minor,
        eligible_months_from_conversion=eligible_months_from_conversion,
        max_payments_per_referral=max_payments_per_referral,
        reward_split=reward_split or {"WALLET": 100},
        confirmation_days=confirmation_days,
        effective_from=effective_from or clock.now(),
        effective_until=effective_until,
        priority=priority,
        status="ACTIVE",
    )
    session.add(rule)
    await session.flush()
    return rule


async def resolve_commission_rule(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    plan_code: str | None = None,
    partner_id: uuid.UUID | None = None,
    partner_type: str | None = None,
    campaign_id: uuid.UUID | None = None,
    billing_reason: str = "initial",
    paid_at: datetime | None = None,
    currency: str = "BDT",
) -> CommissionRule | None:
    """Resolves highest-specificity active commission rule without ties (§9.2, ADR 0022)."""
    check_time = paid_at or clock.now()

    # Load all active rules that overlap in time and match or wildcard fields
    stmt = (
        select(CommissionRule)
        .where(
            CommissionRule.status == "ACTIVE",
            CommissionRule.currency == currency,
            CommissionRule.effective_from <= check_time,
            (CommissionRule.effective_until.is_(None) | (CommissionRule.effective_until > check_time)),
        )
    )
    res = await session.execute(stmt)
    rules = list(res.scalars().all())

    candidate_scores: list[tuple[int, CommissionRule]] = []

    for r in rules:
        # Check constraints (null = wildcard)
        if r.product_id and r.product_id != product_id:
            continue
        if r.plan_code and r.plan_code != plan_code:
            continue
        if r.partner_id and r.partner_id != partner_id:
            continue
        if r.partner_type and r.partner_type != partner_type:
            continue
        if r.campaign_id and r.campaign_id != campaign_id:
            continue
        if r.billing_reason and r.billing_reason != billing_reason:
            continue

        score = calculate_rule_specificity_score(
            r,
            has_partner_match=bool(r.partner_id and r.partner_id == partner_id),
            has_campaign_match=bool(r.campaign_id and r.campaign_id == campaign_id),
            has_partner_type_match=bool(r.partner_type and r.partner_type == partner_type),
            has_plan_match=bool(r.plan_code and r.plan_code == plan_code),
            has_billing_match=bool(r.billing_reason and r.billing_reason == billing_reason),
            has_product_match=bool(r.product_id and r.product_id == product_id),
        )
        candidate_scores.append((score, r))

    if not candidate_scores:
        return None

    # Sort descending by score
    candidate_scores.sort(key=lambda x: x[0], reverse=True)

    top_score, top_rule = candidate_scores[0]

    # Check for ambiguous tie (ADR 0022)
    if len(candidate_scores) > 1:
        second_score, second_rule = candidate_scores[1]
        if second_score == top_score and second_rule.id != top_rule.id:
            raise PlatformError(
                ErrorCode.COMMISSION_RULE_TIE,
                f"Commission rule tie detected between '{top_rule.rule_name}' and '{second_rule.rule_name}' (score {top_score})",
            )

    return top_rule


from app.core.money import apply_bps


# ---------------------------------------------------------------- Commission Math (§9.3, I3)


def calculate_commission_amount(amount_net_paid: int, rule: CommissionRule) -> int:
    """Calculates commission amount using integer minor units and single ROUND_HALF_UP (Invariant I3)."""
    if amount_net_paid < rule.min_net_paid_minor:
        return 0

    if rule.commission_type == "PERCENTAGE":
        commission = apply_bps(amount_net_paid, rule.rate_bps)
    elif rule.commission_type == "FIXED":
        commission = rule.fixed_amount_minor
    else:
        commission = 0

    if rule.max_commission_minor is not None and commission > rule.max_commission_minor:
        commission = rule.max_commission_minor

    return max(0, commission)


# ---------------------------------------------------------------- Commission Processing & Lifecycle


async def get_commission_by_payment(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    payment_id: str,
) -> Commission | None:
    """Lookup commission by product and payment_id."""
    stmt = select(Commission).where(
        Commission.product_id == product_id,
        Commission.payment_id == payment_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_commission_by_id(session: AsyncSession, commission_id: uuid.UUID) -> Commission | None:
    """Lookup commission by primary key."""
    stmt = select(Commission).where(Commission.id == commission_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def process_payment_commission(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    payment_id: str,
    external_user_id: str,
    amount_net_paid: int,
    plan_code: str | None = None,
    billing_reason: str = "initial",
    paid_at: datetime | None = None,
    currency: str = "BDT",
) -> Commission | None:
    """Calculates and creates a pending commission for a payment event (§9, §10)."""
    # 1. Check idempotency on (product_id, payment_id)
    existing = await get_commission_by_payment(session, product_id=product_id, payment_id=payment_id)
    if existing:
        return existing

    # 2. Lookup active attribution
    attr = await referral_service.get_attribution_by_external_user(
        session, product_id=product_id, external_user_id=external_user_id
    )
    if not attr or attr.status not in ("ATTRIBUTED", "TRIALING", "CONVERTED", "ACTIVE"):
        return None  # No referral attribution for this user

    # 3. Resolve commission rule
    earned_time = paid_at or clock.now()
    rule = await resolve_commission_rule(
        session,
        product_id=product_id,
        plan_code=plan_code,
        partner_id=attr.referrer_user_id,
        campaign_id=attr.campaign_id,
        billing_reason=billing_reason,
        paid_at=earned_time,
        currency=currency,
    )
    if not rule:
        return None

    # Check renewal window eligibility (§9.3, §11.3)
    if billing_reason == "renewal":
        max_renewal_days = rule.eligible_months_from_conversion * 30
        if earned_time > attr.registered_at + timedelta(days=max_renewal_days):
            return None

    # 4. Calculate commission
    amount = calculate_commission_amount(amount_net_paid, rule)
    if amount <= 0:
        return None

    # 5. Create Commission (PENDING)
    confirmation_due = earned_time + timedelta(days=rule.confirmation_days)
    snapshot = {
        "rule_id": str(rule.id),
        "rule_name": rule.rule_name,
        "amount_net_paid": amount_net_paid,
        "rate_bps": rule.rate_bps,
        "commission_type": rule.commission_type,
        "confirmation_days": rule.confirmation_days,
        "reward_split": rule.reward_split,
        "earned_at": earned_time.isoformat(),
    }

    commission = Commission(
        rule_id=rule.id,
        referrer_user_id=attr.referrer_user_id,
        product_id=product_id,
        payment_id=payment_id,
        attribution_id=attr.id,
        amount_minor=amount,
        currency=currency,
        status="PENDING",
        earned_at=earned_time,
        confirmation_due_at=confirmation_due,
        calculation_snapshot=snapshot,
    )
    session.add(commission)
    await session.flush()

    # 6. Post double-entry ledger entry P1 (Pending)
    await ledger_service.post_commission_pending(
        session,
        commission_id=commission.id,
        user_id=attr.referrer_user_id,
        amount_minor=amount,
        currency=currency,
    )

    # 7. Update attribution status to CONVERTED if it was ATTRIBUTED
    if attr.status == "ATTRIBUTED":
        attr.status = "CONVERTED"
        await session.flush()

    return commission


async def confirm_commission(session: AsyncSession, *, commission_id: uuid.UUID) -> Commission:
    """Transitions a pending commission to AVAILABLE and posts to ledger (§9.4, §10.2)."""
    comm = await get_commission_by_id(session, commission_id)
    if not comm:
        raise PlatformError(ErrorCode.NOT_FOUND, "Commission not found")

    if comm.status == "AVAILABLE":
        return comm  # Idempotent

    if comm.status != "PENDING":
        raise PlatformError(
            ErrorCode.COMMISSION_STATE_INVALID,
            f"Cannot confirm commission in status '{comm.status}'",
        )

    comm.status = "AVAILABLE"
    comm.confirmed_at = clock.now()
    await session.flush()

    # Post double-entry ledger entry P2 (Confirmed)
    reward_split = comm.calculation_snapshot.get("reward_split", {"WALLET": 100})
    await ledger_service.post_commission_confirmed(
        session,
        commission_id=comm.id,
        user_id=comm.referrer_user_id,
        amount_minor=comm.amount_minor,
        currency=comm.currency,
        reward_split=reward_split,
    )

    return comm


async def reverse_commission(
    session: AsyncSession,
    *,
    commission_id: uuid.UUID,
    reason: str = "REFUND",
) -> Commission:
    """Reverses or cancels a commission on refund/chargeback (§9.4, §10.2)."""
    comm = await get_commission_by_id(session, commission_id)
    if not comm:
        raise PlatformError(ErrorCode.NOT_FOUND, "Commission not found")

    if comm.status in ("CANCELLED", "REVERSED"):
        return comm  # Idempotent

    is_pending = comm.status == "PENDING"
    comm.status = "CANCELLED" if is_pending else "REVERSED"
    await session.flush()

    # Post double-entry ledger entry P3 (Reversal)
    await ledger_service.post_commission_reversal(
        session,
        commission_id=comm.id,
        user_id=comm.referrer_user_id,
        amount_minor=comm.amount_minor,
        is_pending=is_pending,
        currency=comm.currency,
    )

    return comm


async def process_refund_reversal(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    payment_id: str,
    refund_id: str,
    amount_refunded: int,
    currency: str = "BDT",
) -> tuple[Commission | None, int]:
    """Processes proportional commission reversal on payment.refunded (§12, ADR 0008)."""
    comm = await get_commission_by_payment(session, product_id=product_id, payment_id=payment_id)
    if not comm:
        return None, 0

    from app.subscriptions import service as sub_service
    payment_fact = await sub_service.get_payment_fact(session, product_id=product_id, payment_id=payment_id)
    if not payment_fact or payment_fact.amount_net_paid <= 0:
        return None, 0

    from app.core.money import mul_div_round
    # Calculate exact proportional commission to reverse
    reversal_amount = mul_div_round(comm.amount_minor, amount_refunded, payment_fact.amount_net_paid)
    if reversal_amount <= 0:
        return comm, 0

    # Ensure cumulative reversals don't exceed original commission
    reversal_amount = min(reversal_amount, comm.amount_minor)

    # Check cumulative refunded amount for this payment via subscriptions service interface (§3)
    prior_refunded = await sub_service.get_total_refunded_for_payment(
        session, product_id=product_id, payment_id=payment_id
    )
    total_refunded = prior_refunded + amount_refunded

    is_full_refund = total_refunded >= payment_fact.amount_net_paid or reversal_amount >= comm.amount_minor
    is_pending = comm.status == "PENDING"

    if is_full_refund:
        comm.status = "CANCELLED" if is_pending else "REVERSED"
    else:
        comm.status = "PARTIALLY_REVERSED"

    await session.flush()

    await sub_service.record_refund_fact(
        session,
        product_id=product_id,
        data={
            "refund_id": refund_id,
            "payment_id": payment_id,
            "amount_refunded": amount_refunded,
            "currency": currency,
            "refunded_at": clock.now(),
        },
    )

    await ledger_service.post_commission_reversal(
        session,
        commission_id=comm.id,
        user_id=comm.referrer_user_id,
        amount_minor=reversal_amount,
        is_pending=is_pending,
        refund_id=refund_id,
        currency=currency,
    )

    return comm, reversal_amount


async def confirm_due_commissions_batch(session: AsyncSession) -> int:
    """Batch confirmation job for Celery Beat (§9.4): confirms all matured pending commissions."""
    now_dt = clock.now()
    stmt = select(Commission).where(
        Commission.status == "PENDING",
        Commission.confirmation_due_at <= now_dt,
    )
    res = await session.execute(stmt)
    due_commissions = list(res.scalars().all())

    count = 0
    for c in due_commissions:
        await confirm_commission(session, commission_id=c.id)
        count += 1

    return count


async def get_commission_metrics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> tuple[int, int]:
    """Returns (commission_pending_minor, commission_available_minor)."""
    comm_pending_stmt = select(func.coalesce(func.sum(Commission.amount_minor), 0)).where(
        Commission.status == "PENDING"
    )
    comm_avail_stmt = select(func.coalesce(func.sum(Commission.amount_minor), 0)).where(
        Commission.status.in_(["AVAILABLE", "PARTIALLY_REVERSED"])
    )
    if product_id:
        comm_pending_stmt = comm_pending_stmt.where(Commission.product_id == product_id)
        comm_avail_stmt = comm_avail_stmt.where(Commission.product_id == product_id)

    comm_pending = int((await session.execute(comm_pending_stmt)).scalar() or 0)
    comm_available = int((await session.execute(comm_avail_stmt)).scalar() or 0)
    return comm_pending, comm_available


async def get_all_commissions(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> list[Commission]:
    """Returns all commissions for reporting."""
    stmt = select(Commission)
    if product_id:
        stmt = stmt.where(Commission.product_id == product_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())

