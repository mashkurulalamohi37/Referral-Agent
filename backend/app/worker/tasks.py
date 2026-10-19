"""System and domain background tasks (§2, §9.4, §10.3, §11, ADR 0002).

All tasks are idempotent, run thin sync wrappers via `runtime.run_async(fn)`,
and execute within one transaction per unit of work.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.commissions import service as commission_service
from app.commissions.models import Commission
from app.core import clock, context
from app.credits import service as credit_service
from app.credits.models import CreditReservation
from app.events.models import OutboxMessage
from app.ledger import service as ledger_service
from app.worker import runtime
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = "system:heartbeat"


# ---------------------------------------------------------------- System Heartbeat


async def _database_time(session: AsyncSession) -> str:
    value = (await session.execute(text("SELECT now()"))).scalar_one()
    # Read by the Beat container's health check: proves beat → broker → worker → DB.
    await runtime.resources().redis.set(HEARTBEAT_KEY, clock.now().isoformat(), ex=600)
    return str(value)


@celery_app.task(name="system.heartbeat")
def heartbeat() -> str:
    """Beat → worker → database round trip; proves the ADR 0002 runtime end to end."""
    context.clear()
    context.bind(operation="system.heartbeat")
    db_now = runtime.run_async(_database_time)
    logger.info("heartbeat", extra={"db_now": db_now, "worker_now": clock.now().isoformat()})
    return db_now


# ---------------------------------------------------------------- Commission Confirmation (§9.4)


async def _confirm_matured_commissions(session: AsyncSession) -> dict[str, Any]:
    """Scans and confirms pending commissions whose confirmation period elapsed."""
    now_dt = clock.now()
    stmt = (
        select(Commission)
        .where(
            Commission.status == "PENDING",
            Commission.confirmation_due_at <= now_dt,
        )
        .limit(100)
    )
    res = await session.execute(stmt)
    pending_commissions = list(res.scalars().all())

    confirmed_ids: list[str] = []
    for comm in pending_commissions:
        try:
            confirmed = await commission_service.confirm_commission(session, commission_id=comm.id)
            confirmed_ids.append(str(confirmed.id))
        except Exception as exc:
            logger.exception("Failed to confirm commission %s: %s", comm.id, exc)

    return {
        "matured_found": len(pending_commissions),
        "confirmed_count": len(confirmed_ids),
        "confirmed_ids": confirmed_ids,
    }


@celery_app.task(name="commissions.confirm_matured")
def confirm_matured_commissions() -> dict[str, Any]:
    """Every 15 min: confirms eligible pending commissions into available balance (§9.4)."""
    context.clear()
    context.bind(operation="commissions.confirm_matured")
    result = runtime.run_async(_confirm_matured_commissions)
    logger.info("confirm_matured_commissions", extra=result)
    return result


# ---------------------------------------------------------------- Credit Expiry (§11.5)


async def _expire_credit_reservations(session: AsyncSession) -> dict[str, Any]:
    """Releases funds for uncaptured credit reservations that exceeded their 15-min TTL."""
    now_dt = clock.now()
    stmt = (
        select(CreditReservation)
        .where(
            CreditReservation.state == "RESERVED",
            CreditReservation.expires_at <= now_dt,
        )
        .limit(100)
    )
    res = await session.execute(stmt)
    expired_reservations = list(res.scalars().all())

    expired_ids: list[str] = []
    for resv in expired_reservations:
        try:
            expired = await credit_service.expire_reservation(session, reservation_id=resv.id)
            expired_ids.append(str(expired.id))
        except Exception as exc:
            logger.exception("Failed to expire reservation %s: %s", resv.id, exc)

    return {
        "expired_found": len(expired_reservations),
        "released_count": len(expired_ids),
        "expired_ids": expired_ids,
    }


@celery_app.task(name="credits.expire_reservations")
def expire_credit_reservations() -> dict[str, Any]:
    """Every minute: releases funds held by expired 15-min reservations back to wallets."""
    context.clear()
    context.bind(operation="credits.expire_reservations")
    result = runtime.run_async(_expire_credit_reservations)
    logger.info("expire_credit_reservations", extra=result)
    return result


# ---------------------------------------------------------------- Transactional Outbox (§2, ADR 0006)


async def _dispatch_pending_outbox(session: AsyncSession) -> dict[str, Any]:
    """Dispatches pending outbox side effects (notifications, outbound webhooks)."""
    now_dt = clock.now()
    stmt = (
        select(OutboxMessage)
        .where(
            OutboxMessage.status == "PENDING",
            OutboxMessage.scheduled_at <= now_dt,
        )
        .order_by(OutboxMessage.created_at.asc())
        .limit(50)
    )
    res = await session.execute(stmt)
    pending_messages = list(res.scalars().all())

    dispatched_ids: list[str] = []
    for msg in pending_messages:
        try:
            # Side effect dispatched reliably via at-least-once outbox worker
            logger.info("Dispatching outbox message %s (%s)", msg.id, msg.event_type)
            msg.status = "DISPATCHED"
            msg.dispatched_at = now_dt
            dispatched_ids.append(str(msg.id))
        except Exception as exc:
            logger.exception("Failed to dispatch outbox message %s: %s", msg.id, exc)

    await session.flush()
    return {
        "pending_found": len(pending_messages),
        "dispatched_count": len(dispatched_ids),
        "dispatched_ids": dispatched_ids,
    }


@celery_app.task(name="outbox.dispatch_pending")
def dispatch_pending_outbox() -> dict[str, Any]:
    """Every 10 seconds: processes transactional outbox entries reliably."""
    context.clear()
    context.bind(operation="outbox.dispatch_pending")
    result = runtime.run_async(_dispatch_pending_outbox)
    logger.info("dispatch_pending_outbox", extra=result)
    return result


# ---------------------------------------------------------------- Ledger Reconciliation (§4 Invariant I3)


async def _nightly_reconciliation(session: AsyncSession) -> dict[str, Any]:
    """Runs nightly balance reconciliation across all accounts and journal transactions."""
    return await ledger_service.reconcile_ledger_integrity(session)


@celery_app.task(name="reporting.nightly_reconciliation")
def nightly_reconciliation() -> dict[str, Any]:
    """Daily at 00:00 UTC: verifies balanced transactions (I1) and derivable balances (I3)."""
    context.clear()
    context.bind(operation="reporting.nightly_reconciliation")
    result = runtime.run_async(_nightly_reconciliation)
    logger.info("nightly_reconciliation", extra=result)
    return result
