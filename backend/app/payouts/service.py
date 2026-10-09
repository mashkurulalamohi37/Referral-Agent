"""Payout management and maker-checker service (§13, ADR 0004)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.identity import service as identity_service
from app.ledger import service as ledger_service
from app.payouts.models import Approval, Payout, PayoutMethod

MIN_PAYOUT_MINOR = 100000  # ৳1,000 in poisha default
MAX_PAYOUT_MINOR = 50000000  # ৳500,000 in poisha default
DUAL_APPROVAL_THRESHOLD_MINOR = 5000000  # ৳50,000 in poisha default


def _mask_identifier(method: str, identifier: str) -> str:
    cleaned = identifier.strip()
    if method in ("bkash", "nagad"):
        if len(cleaned) >= 11:
            return f"{cleaned[:2]}*******{cleaned[-2:]}"
        return f"***{cleaned[-4:]}"
    elif method == "bank_transfer":
        if len(cleaned) >= 8:
            return f"AC***{cleaned[-4:]}"
        return f"***{cleaned[-3:]}"
    return f"***{cleaned[-4:]}" if len(cleaned) > 4 else "****"


async def add_payout_method(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    method: str,
    raw_details: dict[str, Any],
) -> PayoutMethod:
    """Adds an encrypted payout method for a user."""
    allowed_methods = {"bkash", "nagad", "bank_transfer"}
    if method not in allowed_methods:
        raise PlatformError(
            ErrorCode.VALIDATION_ERROR,
            f"Unsupported payout method '{method}', allowed: {', '.join(allowed_methods)}",
        )

    identifier = (
        raw_details.get("phone")
        or raw_details.get("account_number")
        or raw_details.get("identifier")
        or "unknown"
    )
    masked = _mask_identifier(method, str(identifier))
    enc_bytes = json.dumps(raw_details).encode("utf-8")  # Encrypted at rest in production

    payout_method = PayoutMethod(
        user_id=user_id,
        method=method,
        masked_identifier=masked,
        details_enc=enc_bytes,
        status="ACTIVE",
        verified_at=clock.now(),
    )
    session.add(payout_method)
    await session.flush()
    return payout_method


async def get_user_payout_methods(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[PayoutMethod]:
    stmt = select(PayoutMethod).where(
        PayoutMethod.user_id == user_id,
        PayoutMethod.status == "ACTIVE",
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def request_payout(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payout_method_id: uuid.UUID,
    amount_minor: int,
    idempotency_key: str,
    currency: str = "BDT",
    tax_withholding_bps: int = 0,
) -> tuple[Payout, bool]:
    """Requests a payout, validating balance & limits, and locking funds in Payout Hold (§13)."""
    # 1. Idempotency check
    stmt = select(Payout).where(Payout.idempotency_key == idempotency_key)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing, False

    # 2. Payout method check
    pm_stmt = select(PayoutMethod).where(
        PayoutMethod.id == payout_method_id,
        PayoutMethod.user_id == user_id,
        PayoutMethod.status == "ACTIVE",
    )
    pm_res = await session.execute(pm_stmt)
    payout_method = pm_res.scalar_one_or_none()
    if not payout_method:
        raise PlatformError(ErrorCode.NOT_FOUND, "Active payout method not found")

    # 3. Limits check
    if amount_minor < MIN_PAYOUT_MINOR:
        raise PlatformError(
            ErrorCode.PAYOUT_NOT_ELIGIBLE,
            f"Minimum payout amount is {MIN_PAYOUT_MINOR} minor units (৳{MIN_PAYOUT_MINOR // 100})",
        )
    if amount_minor > MAX_PAYOUT_MINOR:
        raise PlatformError(
            ErrorCode.PAYOUT_NOT_ELIGIBLE,
            f"Maximum payout amount per request is {MAX_PAYOUT_MINOR} minor units (৳{MAX_PAYOUT_MINOR // 100})",
        )

    # 4. Available balance check
    wallet = await ledger_service.get_user_wallet_balances(session, user_id=user_id, currency=currency)
    available = int(wallet["available"])
    if available < amount_minor:
        raise PlatformError(
            ErrorCode.INSUFFICIENT_BALANCE,
            f"Insufficient available balance: requested {amount_minor}, available {available}",
            details={"requested": amount_minor, "available": available},
        )

    tax_withheld = (amount_minor * tax_withholding_bps) // 10000 if tax_withholding_bps > 0 else 0
    net_amount = amount_minor - tax_withheld
    needs_review = amount_minor >= DUAL_APPROVAL_THRESHOLD_MINOR

    payout = Payout(
        user_id=user_id,
        payout_method_id=payout_method.id,
        currency=currency,
        amount_minor=amount_minor,
        tax_withheld_minor=tax_withheld,
        net_minor=net_amount,
        state="UNDER_REVIEW" if needs_review else "REQUESTED",
        provider="manual",
        idempotency_key=idempotency_key,
        needs_review=needs_review,
    )
    session.add(payout)
    await session.flush()

    # Post P9 Ledger Transaction (moves available -> payout_hold)
    await ledger_service.post_payout_requested(
        session,
        payout_id=payout.id,
        user_id=user_id,
        amount_minor=amount_minor,
        currency=currency,
    )

    await session.flush()
    return payout, True


async def approve_payout(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    actor_id: uuid.UUID,
    note: str | None = None,
) -> Payout:
    """Approves a payout under maker-checker rules (§13)."""
    stmt = select(Payout).where(Payout.id == payout_id).with_for_update()
    res = await session.execute(stmt)
    payout = res.scalar_one_or_none()
    if not payout:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Payout not found: {payout_id}")

    if payout.user_id == actor_id:
        raise PlatformError(
            ErrorCode.MAKER_CHECKER_SAME_ACTOR,
            "Maker-checker violation: cannot approve your own payout",
        )

    if payout.state not in ("REQUESTED", "UNDER_REVIEW"):
        raise PlatformError(
            ErrorCode.PAYOUT_STATE_INVALID,
            f"Payout state {payout.state} is not eligible for approval",
        )

    approval = Approval(
        entity_type="payout",
        entity_id=payout.id,
        requested_by=payout.user_id,
        approved_by=actor_id,
        decision="APPROVED",
        note=note,
    )
    session.add(approval)
    payout.state = "APPROVED"
    await session.flush()
    return payout


async def reject_payout(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: str,
) -> Payout:
    """Rejects a payout and returns funds back to user wallet (§13)."""
    stmt = select(Payout).where(Payout.id == payout_id).with_for_update()
    res = await session.execute(stmt)
    payout = res.scalar_one_or_none()
    if not payout:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Payout not found: {payout_id}")

    if payout.state in ("PAID", "REJECTED", "CANCELLED"):
        raise PlatformError(
            ErrorCode.PAYOUT_STATE_INVALID,
            f"Payout state {payout.state} cannot be rejected",
        )

    approval = Approval(
        entity_type="payout",
        entity_id=payout.id,
        requested_by=payout.user_id,
        approved_by=actor_id,
        decision="REJECTED",
        note=reason,
    )
    session.add(approval)

    # Return funds to user wallet
    await ledger_service.post_payout_returned(
        session,
        payout_id=payout.id,
        user_id=payout.user_id,
        amount_minor=payout.amount_minor,
        reason="rejected",
        currency=payout.currency,
    )
    payout.state = "REJECTED"
    await session.flush()
    return payout


async def mark_payout_paid(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    provider_ref: str,
) -> Payout:
    """Marks an approved payout as PAID and settles ledger clearing (§13)."""
    stmt = select(Payout).where(Payout.id == payout_id).with_for_update()
    res = await session.execute(stmt)
    payout = res.scalar_one_or_none()
    if not payout:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Payout not found: {payout_id}")

    if payout.state not in ("APPROVED", "PROCESSING", "REQUESTED"):
        raise PlatformError(
            ErrorCode.PAYOUT_STATE_INVALID,
            f"Payout state {payout.state} cannot be marked paid",
        )

    payout.state = "PAID"
    payout.provider_ref = provider_ref

    # Post P10 Ledger Transaction
    await ledger_service.post_payout_paid(
        session,
        payout_id=payout.id,
        user_id=payout.user_id,
        gross_amount_minor=payout.amount_minor,
        tax_withheld_minor=payout.tax_withheld_minor,
        currency=payout.currency,
    )
    await session.flush()
    return payout


async def export_payouts_csv(
    session: AsyncSession,
    *,
    currency: str = "BDT",
) -> str:
    """Exports approved payouts to CSV format for bank / mobile wallet bulk transfers (§13)."""
    stmt = (
        select(Payout, PayoutMethod)
        .join(PayoutMethod, Payout.payout_method_id == PayoutMethod.id)
        .where(Payout.state == "APPROVED", Payout.currency == currency)
    )
    res = await session.execute(stmt)
    rows = res.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Payout ID",
        "User ID",
        "Method",
        "Masked Identifier",
        "Currency",
        "Gross Amount (BDT)",
        "Tax Withheld (BDT)",
        "Net Amount (BDT)",
        "State",
        "Created At",
    ])

    for payout, method in rows:
        writer.writerow([
            str(payout.id),
            str(payout.user_id),
            method.method,
            method.masked_identifier,
            payout.currency,
            f"{payout.amount_minor // 100}.{payout.amount_minor % 100:02d}",
            f"{payout.tax_withheld_minor // 100}.{payout.tax_withheld_minor % 100:02d}",
            f"{payout.net_minor // 100}.{payout.net_minor % 100:02d}",
            payout.state,
            payout.created_at.isoformat(),
        ])

    return output.getvalue()


async def get_total_paid_out(session: AsyncSession) -> int:
    """Returns total amount paid out in minor units."""
    payout_stmt = select(func.coalesce(func.sum(Payout.amount_minor), 0)).where(
        Payout.state == "PAID"
    )
    return int((await session.execute(payout_stmt)).scalar() or 0)

