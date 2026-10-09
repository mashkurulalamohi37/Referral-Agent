"""Credits and subscription reservation service (§11, ADR 0011)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.credits.models import CreditRefund, CreditReservation
from app.ledger import service as ledger_service


async def get_spendable_balance(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
    currency: str = "BDT",
) -> dict[str, Any]:
    """Calculates spendable credit balance for a product account."""
    prod_account = await catalog_service.get_product_account(
        session, product_id=product_id, external_user_id=external_user_id
    )
    if not prod_account or not prod_account.user_id:
        return {
            "spendable_minor": 0,
            "credit_only_minor": 0,
            "available_minor": 0,
            "user_id": None,
            "currency": currency,
        }

    wallet = await ledger_service.get_user_wallet_balances(
        session, user_id=prod_account.user_id, currency=currency
    )
    available = max(0, int(wallet["available"]))
    credit_only = max(0, int(wallet["credit_only"]))
    spendable = credit_only + available

    return {
        "spendable_minor": spendable,
        "credit_only_minor": credit_only,
        "available_minor": available,
        "user_id": prod_account.user_id,
        "currency": currency,
    }


async def create_reservation(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    external_user_id: str,
    requested_amount: int,
    order_ref: str,
    idempotency_key: str,
    currency: str = "BDT",
    ttl_minutes: int = 15,
) -> tuple[CreditReservation, bool]:
    """Creates a credit reservation with two-phase locking (§11)."""
    # 1. Idempotency check
    stmt = select(CreditReservation).where(
        CreditReservation.product_id == product_id,
        CreditReservation.idempotency_key == idempotency_key,
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing, False

    # 2. Product account lookup
    prod_account = await catalog_service.get_product_account(
        session, product_id=product_id, external_user_id=external_user_id
    )
    if not prod_account or not prod_account.user_id:
        raise PlatformError(
            ErrorCode.CREDIT_ACCOUNT_NOT_LINKED,
            "No referrer user linked to this product account to draw credit from",
        )

    # 3. Spendable calculation
    wallet = await ledger_service.get_user_wallet_balances(
        session, user_id=prod_account.user_id, currency=currency
    )
    available = max(0, int(wallet["available"]))
    credit_only = max(0, int(wallet["credit_only"]))
    spendable = credit_only + available

    if spendable <= 0 or requested_amount <= 0:
        raise PlatformError(
            ErrorCode.INSUFFICIENT_BALANCE,
            "Insufficient spendable credit for reservation",
            details={"requested": requested_amount, "spendable": spendable},
        )

    reserved_minor = min(requested_amount, spendable)

    # Draw from credit_only first, then available
    from_credit_only = min(credit_only, reserved_minor)
    from_available = reserved_minor - from_credit_only

    expires_at = clock.now() + timedelta(minutes=ttl_minutes)

    reservation = CreditReservation(
        product_id=product_id,
        idempotency_key=idempotency_key,
        product_account_id=prod_account.id,
        user_id=prod_account.user_id,
        order_ref=order_ref,
        currency=currency,
        requested_minor=requested_amount,
        reserved_minor=reserved_minor,
        from_credit_only_minor=from_credit_only,
        from_available_minor=from_available,
        state="RESERVED",
        expires_at=expires_at,
    )
    session.add(reservation)
    await session.flush()

    # Post ledger transaction
    await ledger_service.post_credit_reserved(
        session,
        reservation_id=reservation.id,
        user_id=prod_account.user_id,
        from_credit_only_minor=from_credit_only,
        from_available_minor=from_available,
        currency=currency,
    )

    await session.flush()
    return reservation, True


async def capture_reservation(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    captured_minor: int | None = None,
    payment_id: str | None = None,
) -> CreditReservation:
    """Captures a reserved credit (§11, ADR 0011)."""
    stmt = (
        select(CreditReservation)
        .where(CreditReservation.id == reservation_id)
        .with_for_update()
    )
    res = await session.execute(stmt)
    reservation = res.scalar_one_or_none()
    if not reservation:
        raise PlatformError(
            ErrorCode.NOT_FOUND,
            f"Credit reservation not found: {reservation_id}",
        )

    if reservation.state in ("CAPTURED", "PARTIALLY_CAPTURED"):
        return reservation

    if reservation.state in ("RELEASED", "EXPIRED"):
        # ADR 0011 Late Capture
        target_capture = captured_minor if captured_minor is not None else reservation.reserved_minor
        reservation.late_captured_minor = target_capture
        reservation.captured_minor = target_capture
        reservation.payment_id = payment_id
        reservation.state = "LATE_CAPTURED"
        await session.flush()
        return reservation

    if reservation.state == "RESERVED":
        target_capture = captured_minor if captured_minor is not None else reservation.reserved_minor
        if target_capture > reservation.reserved_minor:
            raise PlatformError(
                ErrorCode.VALIDATION_ERROR,
                f"Cannot capture {target_capture} minor units, exceeded reserved amount {reservation.reserved_minor}",
            )

        # 1. Post capture
        await ledger_service.post_credit_captured(
            session,
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            product_id=reservation.product_id,
            captured_minor=target_capture,
            payment_id=payment_id,
            currency=reservation.currency,
        )

        # 2. Release uncaptured remainder if partial capture
        uncaptured = reservation.reserved_minor - target_capture
        if uncaptured > 0:
            rel_avail = min(reservation.from_available_minor, uncaptured)
            rel_cred = uncaptured - rel_avail
            await ledger_service.post_credit_released(
                session,
                reservation_id=reservation.id,
                user_id=reservation.user_id,
                release_credit_only_minor=rel_cred,
                release_available_minor=rel_avail,
                currency=reservation.currency,
            )
            reservation.state = "PARTIALLY_CAPTURED"
        else:
            reservation.state = "CAPTURED"

        reservation.captured_minor = target_capture
        reservation.payment_id = payment_id
        await session.flush()

    return reservation


async def release_reservation(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
) -> CreditReservation:
    """Releases a credit reservation back to user wallet."""
    stmt = (
        select(CreditReservation)
        .where(CreditReservation.id == reservation_id)
        .with_for_update()
    )
    res = await session.execute(stmt)
    reservation = res.scalar_one_or_none()
    if not reservation:
        raise PlatformError(
            ErrorCode.NOT_FOUND,
            f"Credit reservation not found: {reservation_id}",
        )

    if reservation.state != "RESERVED":
        return reservation

    await ledger_service.post_credit_released(
        session,
        reservation_id=reservation.id,
        user_id=reservation.user_id,
        release_credit_only_minor=reservation.from_credit_only_minor,
        release_available_minor=reservation.from_available_minor,
        currency=reservation.currency,
    )
    reservation.state = "RELEASED"
    await session.flush()
    return reservation


async def refund_credit(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    reservation_id: uuid.UUID,
    amount_minor: int,
    idempotency_key: str,
    currency: str = "BDT",
) -> tuple[CreditRefund, bool]:
    """Refunds previously captured subscription credit (§12)."""
    # 1. Idempotency check
    stmt = select(CreditRefund).where(
        CreditRefund.product_id == product_id,
        CreditRefund.idempotency_key == idempotency_key,
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing, False

    # 2. Reservation check
    stmt = select(CreditReservation).where(CreditReservation.id == reservation_id)
    res = await session.execute(stmt)
    reservation = res.scalar_one_or_none()
    if not reservation:
        raise PlatformError(
            ErrorCode.NOT_FOUND,
            f"Credit reservation not found: {reservation_id}",
        )

    # Check cumulative refunds
    sum_stmt = select(func.coalesce(func.sum(CreditRefund.amount_minor), 0)).where(
        CreditRefund.credit_reservation_id == reservation_id
    )
    sum_res = await session.execute(sum_stmt)
    cum_refunded = int(sum_res.scalar() or 0)

    if cum_refunded + amount_minor > reservation.captured_minor:
        raise PlatformError(
            ErrorCode.CREDIT_REFUND_EXCEEDS_CAPTURED,
            f"Cumulative credit refund ({cum_refunded + amount_minor}) exceeds captured credit ({reservation.captured_minor})",
        )

    refund = CreditRefund(
        product_id=product_id,
        idempotency_key=idempotency_key,
        credit_reservation_id=reservation_id,
        amount_minor=amount_minor,
        currency=currency,
    )
    session.add(refund)
    await session.flush()

    # Post ledger refund
    tx, _ = await ledger_service.post_credit_refunded(
        session,
        refund_id=refund.id,
        user_id=reservation.user_id,
        product_id=product_id,
        amount_minor=amount_minor,
        refund_to_credit_only=True,
        currency=currency,
    )
    refund.journal_transaction_id = tx.id
    await session.flush()
    return refund, True


async def expire_stale_reservations(session: AsyncSession) -> int:
    """Expires all past-TTL reservations and releases reserved funds."""
    stmt = (
        select(CreditReservation)
        .where(
            CreditReservation.state == "RESERVED",
            CreditReservation.expires_at < clock.now(),
        )
        .with_for_update()
    )
    res = await session.execute(stmt)
    stale = res.scalars().all()
    count = 0
    for reservation in stale:
        await ledger_service.post_credit_released(
            session,
            reservation_id=reservation.id,
            user_id=reservation.user_id,
            release_credit_only_minor=reservation.from_credit_only_minor,
            release_available_minor=reservation.from_available_minor,
            currency=reservation.currency,
        )
        reservation.state = "EXPIRED"
        count += 1
    await session.flush()
    return count
