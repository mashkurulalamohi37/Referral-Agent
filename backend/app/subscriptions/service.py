"""Subscriptions and Payments public service interface (§8.3, §21, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.subscriptions.models import PaymentFact, RefundFact, Subscription


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    return None


# ---------------------------------------------------------------- Subscription Queries & Mutations


async def get_subscription(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    subscription_id: str,
) -> Subscription | None:
    """Fetches a subscription by product and subscription_id."""
    stmt = select(Subscription).where(
        Subscription.product_id == product_id,
        Subscription.subscription_id == subscription_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def process_subscription_event(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    event_type: str,
    data: dict[str, Any],
) -> Subscription:
    """Processes subscription lifecycle events (created, updated, cancelled, expired)."""
    sub_id = data["subscription_id"]
    external_user_id = data.get("external_user_id")
    plan_code = data.get("plan_code")
    status = data.get("status", "ACTIVE")

    existing = await get_subscription(session, product_id=product_id, subscription_id=sub_id)

    period_start = _parse_dt(data.get("period_start"))
    period_end = _parse_dt(data.get("period_end"))
    effective_at = _parse_dt(data.get("effective_at"))

    if event_type == "subscription.created":
        if existing:
            return existing

        prod_account, _ = await catalog_service.get_or_create_product_account(
            session, product_id=product_id, external_user_id=external_user_id or "unknown"
        )
        sub = Subscription(
            product_id=product_id,
            product_account_id=prod_account.id,
            subscription_id=sub_id,
            external_user_id=external_user_id or "unknown",
            plan_code=plan_code or "default",
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            metadata_json=data.get("metadata", {}),
        )
        session.add(sub)
        await session.flush()
        return sub

    if not existing:
        prod_account, _ = await catalog_service.get_or_create_product_account(
            session, product_id=product_id, external_user_id=external_user_id or "unknown"
        )
        existing = Subscription(
            product_id=product_id,
            product_account_id=prod_account.id,
            subscription_id=sub_id,
            external_user_id=external_user_id or "unknown",
            plan_code=plan_code or "default",
            status=status,
            metadata_json=data.get("metadata", {}),
        )
        session.add(existing)

    if event_type == "subscription.updated":
        if plan_code:
            existing.plan_code = plan_code
        if status:
            existing.status = status
        if period_start is not None:
            existing.current_period_start = period_start
        if period_end is not None:
            existing.current_period_end = period_end

    elif event_type == "subscription.cancelled":
        existing.status = "CANCELLED"
        existing.cancelled_at = effective_at or clock.now()

    elif event_type == "subscription.expired":
        existing.status = "EXPIRED"

    await session.flush()
    return existing


# ---------------------------------------------------------------- Payment Queries & Facts


async def get_payment_fact(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    payment_id: str,
) -> PaymentFact | None:
    """Lookup payment fact by product and payment_id."""
    stmt = select(PaymentFact).where(
        PaymentFact.product_id == product_id,
        PaymentFact.payment_id == payment_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def record_payment_fact(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    data: dict[str, Any],
) -> PaymentFact:
    """Records an immutable payment fact derived from payment.succeeded."""
    payment_id = data["payment_id"]
    existing = await get_payment_fact(session, product_id=product_id, payment_id=payment_id)
    if existing:
        return existing

    paid_at = _parse_dt(data.get("paid_at")) or clock.now()

    credit_res_id = None
    if data.get("credit_reservation_id"):
        credit_res_id = uuid.UUID(data["credit_reservation_id"]) if isinstance(data["credit_reservation_id"], str) else data["credit_reservation_id"]

    fact = PaymentFact(
        product_id=product_id,
        payment_id=payment_id,
        subscription_id=data.get("subscription_id"),
        external_user_id=data["external_user_id"],
        plan_code=data.get("plan_code"),
        billing_reason=data.get("billing_reason", "initial"),
        currency=data.get("currency", "BDT"),
        amount_gross=int(data["amount_gross"]),
        discount_amount=int(data.get("discount_amount", 0)),
        tax_amount=int(data.get("tax_amount", 0)),
        credit_applied_amount=int(data.get("credit_applied_amount", 0)),
        credit_reservation_id=credit_res_id,
        amount_net_paid=int(data["amount_net_paid"]),
        paid_at=paid_at,
        payment_fingerprint=data.get("payment_fingerprint"),
    )
    session.add(fact)
    await session.flush()
    return fact


async def get_total_refunded_for_payment(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    payment_id: str,
) -> int:
    """Returns the cumulative refunded amount for a payment in minor units."""
    from sqlalchemy import func
    stmt = select(func.coalesce(func.sum(RefundFact.amount_refunded), 0)).where(
        RefundFact.product_id == product_id,
        RefundFact.payment_id == payment_id,
    )
    res = await session.execute(stmt)
    return int(res.scalar() or 0)


async def record_refund_fact(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    data: dict[str, Any],
) -> RefundFact:
    """Records an immutable refund fact derived from payment.refunded."""
    refund_id = data["refund_id"]
    stmt = select(RefundFact).where(
        RefundFact.product_id == product_id,
        RefundFact.refund_id == refund_id,
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    refunded_at = _parse_dt(data.get("refunded_at")) or clock.now()

    refund = RefundFact(
        product_id=product_id,
        refund_id=refund_id,
        payment_id=data["payment_id"],
        currency=data.get("currency", "BDT"),
        amount_refunded=int(data["amount_refunded"]),
        refunded_at=refunded_at,
        reason=data.get("reason"),
    )
    session.add(refund)
    await session.flush()
    return refund


async def get_revenue_metrics(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
) -> tuple[int, int, int]:
    """Returns (gross_revenue_minor, net_revenue_minor, credit_redeemed_minor)."""
    from sqlalchemy import func

    pay_stmt = select(
        func.coalesce(func.sum(PaymentFact.amount_gross), 0),
        func.coalesce(func.sum(PaymentFact.amount_net_paid), 0),
        func.coalesce(func.sum(PaymentFact.credit_applied_amount), 0),
    )
    if product_id:
        pay_stmt = pay_stmt.where(PaymentFact.product_id == product_id)
    gross_rev, net_rev, credit_redeemed = (await session.execute(pay_stmt)).one()
    return int(gross_rev), int(net_rev), int(credit_redeemed)

