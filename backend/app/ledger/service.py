"""Double-entry ledger public service interface (§10, ADR 0007, Invariant I1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.ledger.models import JournalTransaction, LedgerAccount, LedgerEntry


# ---------------------------------------------------------------- Account Management


async def get_or_create_account(
    session: AsyncSession,
    *,
    account_number: str,
    account_type: str,
    user_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    currency: str = "BDT",
) -> LedgerAccount:
    """Fetches or creates a chart-of-accounts ledger account."""
    stmt = select(LedgerAccount).where(LedgerAccount.account_number == account_number)
    res = await session.execute(stmt)
    account = res.scalar_one_or_none()
    if account:
        return account

    account = LedgerAccount(
        account_number=account_number,
        account_type=account_type,
        user_id=user_id,
        product_id=product_id,
        currency=currency,
        status="ACTIVE",
    )
    session.add(account)
    await session.flush()
    return account


# ---------------------------------------------------------------- Journal Postings (§10.2, Invariant I1)


async def post_journal_transaction(
    session: AsyncSession,
    *,
    transaction_type: str,
    idempotency_key: str,
    description: str,
    entries: list[dict[str, Any]],
    reference_type: str | None = None,
    reference_id: str | None = None,
    posted_at: datetime | None = None,
) -> tuple[JournalTransaction, bool]:
    """Posts an immutable double-entry journal transaction.

    Invariant I1: sum of entry amounts MUST equal zero.
    """
    # 1. Check idempotency
    stmt = select(JournalTransaction).where(JournalTransaction.idempotency_key == idempotency_key)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing, False

    # 2. Enforce Double-Entry Balance (I1)
    total_balance = sum(int(e["amount"]) for e in entries)
    if total_balance != 0:
        raise PlatformError(
            ErrorCode.LEDGER_UNBALANCED,
            f"Ledger transaction unbalanced: entries sum to {total_balance} minor units, must equal 0",
            details={"entries": entries, "sum": total_balance},
        )

    if len(entries) < 2:
        raise PlatformError(
            ErrorCode.LEDGER_UNBALANCED,
            "Journal transaction must contain at least 2 entries",
        )

    tx = JournalTransaction(
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=str(reference_id) if reference_id else None,
        idempotency_key=idempotency_key,
        description=description,
        posted_at=posted_at or clock.now(),
    )
    session.add(tx)
    await session.flush()

    for entry_dict in entries:
        account_id = entry_dict.get("account_id")
        if not account_id and "account_number" in entry_dict:
            acc = await get_or_create_account(
                session,
                account_number=entry_dict["account_number"],
                account_type=entry_dict.get("account_type", "LIABILITY"),
                user_id=entry_dict.get("user_id"),
                product_id=entry_dict.get("product_id"),
                currency=entry_dict.get("currency", "BDT"),
            )
            account_id = acc.id

        ledger_entry = LedgerEntry(
            transaction_id=tx.id,
            account_id=account_id,
            amount=int(entry_dict["amount"]),
            currency=entry_dict.get("currency", "BDT"),
        )
        session.add(ledger_entry)

    await session.flush()
    return tx, True


# ---------------------------------------------------------------- Standard Business Postings (P1–P4)


async def post_commission_pending(
    session: AsyncSession,
    *,
    commission_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_minor: int,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P1: Post pending commission (Debit Expense, Credit User Pending)."""
    return await post_journal_transaction(
        session,
        transaction_type="COMMISSION_PENDING",
        reference_type="COMMISSION",
        reference_id=str(commission_id),
        idempotency_key=f"tx:comm:pending:{commission_id}",
        description=f"Commission earned pending confirmation ({commission_id})",
        entries=[
            {
                "account_number": f"platform:commission_expense:{currency}",
                "account_type": "EXPENSE",
                "amount": amount_minor,  # Debit +
                "currency": currency,
            },
            {
                "account_number": f"user:pending:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": -amount_minor,  # Credit -
                "currency": currency,
            },
        ],
    )


async def post_commission_confirmed(
    session: AsyncSession,
    *,
    commission_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_minor: int,
    currency: str = "BDT",
    reward_split: dict[str, Any] | None = None,
) -> tuple[JournalTransaction, bool]:
    """P2: Move commission from Pending to Available / Credit-Only."""
    split = reward_split or {"WALLET": 100}
    wallet_pct = int(split.get("WALLET", 100))
    credit_pct = int(split.get("CREDIT_ONLY", 0))

    # Integer split with exact largest-remainder allocation (ADR 0008)
    from app.core.money import allocate
    available_amount, credit_amount = allocate(amount_minor, [wallet_pct, credit_pct])

    entries: list[dict[str, Any]] = [
        {
            "account_number": f"user:pending:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": amount_minor,  # Debit pending + (clearing pending)
            "currency": currency,
        }
    ]

    if available_amount > 0:
        entries.append({
            "account_number": f"user:available:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": -available_amount,  # Credit available -
            "currency": currency,
        })

    if credit_amount > 0:
        entries.append({
            "account_number": f"user:credit_only:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": -credit_amount,  # Credit credit-only -
            "currency": currency,
        })

    return await post_journal_transaction(
        session,
        transaction_type="COMMISSION_CONFIRMED",
        reference_type="COMMISSION",
        reference_id=str(commission_id),
        idempotency_key=f"tx:comm:confirmed:{commission_id}",
        description=f"Commission confirmed and available ({commission_id})",
        entries=entries,
    )


async def post_commission_reversal(
    session: AsyncSession,
    *,
    commission_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_minor: int,
    is_pending: bool,
    refund_id: str | None = None,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P3: Reverse commission on refund/chargeback."""
    source_acc = f"user:pending:{user_id}:{currency}" if is_pending else f"user:available:{user_id}:{currency}"
    key = f"tx:comm:reversed:{commission_id}:{refund_id}" if refund_id else f"tx:comm:reversed:{commission_id}"

    return await post_journal_transaction(
        session,
        transaction_type="COMMISSION_REVERSED",
        reference_type="COMMISSION",
        reference_id=str(commission_id),
        idempotency_key=key,
        description=f"Commission reversed ({commission_id})",
        entries=[
            {
                "account_number": source_acc,
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": amount_minor,  # Debit user liability +
                "currency": currency,
            },
            {
                "account_number": f"platform:commission_expense:{currency}",
                "account_type": "EXPENSE",
                "amount": -amount_minor,  # Credit expense -
                "currency": currency,
            },
        ],
    )


# ---------------------------------------------------------------- User Balance Aggregation


async def get_raw_account_balance(session: AsyncSession, account_number: str) -> int:
    """Computes exact sum of ledger entries for an account."""
    stmt = (
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .join(LedgerAccount, LedgerEntry.account_id == LedgerAccount.id)
        .where(LedgerAccount.account_number == account_number)
    )
    res = await session.execute(stmt)
    return int(res.scalar() or 0)


async def get_user_wallet_balances(
    session: AsyncSession,
    user_id: uuid.UUID,
    currency: str = "BDT",
) -> dict[str, Any]:
    """Returns partner wallet balances in minor units (§10.1).

    In double-entry liability accounts, credit entries are negative.
    User available balance = -sum(user:available entries).
    """
    pending_raw = await get_raw_account_balance(session, f"user:pending:{user_id}:{currency}")
    available_raw = await get_raw_account_balance(session, f"user:available:{user_id}:{currency}")
    credit_only_raw = await get_raw_account_balance(session, f"user:credit_only:{user_id}:{currency}")
    reserved_raw = await get_raw_account_balance(session, f"user:reserved:{user_id}:{currency}")
    payout_hold_raw = await get_raw_account_balance(session, f"user:payout_hold:{user_id}:{currency}")

    return {
        "user_id": str(user_id),
        "currency": currency,
        "pending": -pending_raw,
        "available": -available_raw,
        "credit_only": -credit_only_raw,
        "reserved": -reserved_raw,
        "payout_hold": -payout_hold_raw,
        "total_earned": -(pending_raw + available_raw + credit_only_raw + reserved_raw + payout_hold_raw),
    }


# ---------------------------------------------------------------- Credit Postings (P5–P8, §10.2)


async def post_credit_reserved(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    from_credit_only_minor: int,
    from_available_minor: int,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P5: Move credit from User Credit-Only / Available to User Reserved."""
    total_reserved = from_credit_only_minor + from_available_minor
    entries: list[dict[str, Any]] = []

    if from_credit_only_minor > 0:
        entries.append({
            "account_number": f"user:credit_only:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": from_credit_only_minor,  # Debit + (reduces credit_only liability)
            "currency": currency,
        })

    if from_available_minor > 0:
        entries.append({
            "account_number": f"user:available:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": from_available_minor,  # Debit + (reduces available liability)
            "currency": currency,
        })

    entries.append({
        "account_number": f"user:reserved:{user_id}:{currency}",
        "account_type": "LIABILITY",
        "user_id": user_id,
        "amount": -total_reserved,  # Credit - (increases reserved liability)
        "currency": currency,
    })

    return await post_journal_transaction(
        session,
        transaction_type="CREDIT_RESERVED",
        reference_type="RESERVATION",
        reference_id=str(reservation_id),
        idempotency_key=f"tx:credit:reserved:{reservation_id}",
        description=f"Subscription credit reserved ({reservation_id})",
        entries=entries,
    )


async def post_credit_captured(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    captured_minor: int,
    payment_id: str | None = None,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P6: Move captured credit from User Reserved to Platform Credit Redeemed."""
    key = f"tx:credit:captured:{reservation_id}:{payment_id}" if payment_id else f"tx:credit:captured:{reservation_id}"
    return await post_journal_transaction(
        session,
        transaction_type="CREDIT_CAPTURED",
        reference_type="RESERVATION",
        reference_id=str(reservation_id),
        idempotency_key=key,
        description=f"Subscription credit captured ({reservation_id})",
        entries=[
            {
                "account_number": f"user:reserved:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": captured_minor,  # Debit + (clears reserved liability)
                "currency": currency,
            },
            {
                "account_number": f"platform:credit_redeemed:{product_id}:{currency}",
                "account_type": "EXPENSE",
                "product_id": product_id,
                "amount": -captured_minor,  # Credit -
                "currency": currency,
            },
        ],
    )


async def post_credit_released(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    release_credit_only_minor: int,
    release_available_minor: int,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P7: Return released credit from User Reserved to User Credit-Only / Available."""
    total_released = release_credit_only_minor + release_available_minor
    entries: list[dict[str, Any]] = [
        {
            "account_number": f"user:reserved:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": total_released,  # Debit + (clears reserved)
            "currency": currency,
        }
    ]

    if release_credit_only_minor > 0:
        entries.append({
            "account_number": f"user:credit_only:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": -release_credit_only_minor,  # Credit - (restores credit_only)
            "currency": currency,
        })

    if release_available_minor > 0:
        entries.append({
            "account_number": f"user:available:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": -release_available_minor,  # Credit - (restores available)
            "currency": currency,
        })

    return await post_journal_transaction(
        session,
        transaction_type="CREDIT_RELEASED",
        reference_type="RESERVATION",
        reference_id=str(reservation_id),
        idempotency_key=f"tx:credit:released:{reservation_id}",
        description=f"Subscription credit released ({reservation_id})",
        entries=entries,
    )


async def post_credit_refunded(
    session: AsyncSession,
    *,
    refund_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    amount_minor: int,
    refund_to_credit_only: bool = True,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P8: Return credit to user upon refund of a payment that used credit."""
    dest_account = (
        f"user:credit_only:{user_id}:{currency}"
        if refund_to_credit_only
        else f"user:available:{user_id}:{currency}"
    )
    return await post_journal_transaction(
        session,
        transaction_type="CREDIT_REFUNDED",
        reference_type="CREDIT_REFUND",
        reference_id=str(refund_id),
        idempotency_key=f"tx:credit:refunded:{refund_id}",
        description=f"Credit refunded to user ({refund_id})",
        entries=[
            {
                "account_number": f"platform:credit_redeemed:{product_id}:{currency}",
                "account_type": "EXPENSE",
                "product_id": product_id,
                "amount": amount_minor,  # Debit + (reverses expense)
                "currency": currency,
            },
            {
                "account_number": dest_account,
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": -amount_minor,  # Credit - (returns to user)
                "currency": currency,
            },
        ],
    )


# ---------------------------------------------------------------- Payout Postings (P9–P11, §10.2)


async def post_payout_requested(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_minor: int,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P9: Move funds from User Available to User Payout Hold."""
    return await post_journal_transaction(
        session,
        transaction_type="PAYOUT_REQUESTED",
        reference_type="PAYOUT",
        reference_id=str(payout_id),
        idempotency_key=f"tx:payout:requested:{payout_id}",
        description=f"Payout requested ({payout_id})",
        entries=[
            {
                "account_number": f"user:available:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": amount_minor,  # Debit available + (reduces available liability)
                "currency": currency,
            },
            {
                "account_number": f"user:payout_hold:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": -amount_minor,  # Credit payout_hold - (holds funds)
                "currency": currency,
            },
        ],
    )


async def post_payout_paid(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    user_id: uuid.UUID,
    gross_amount_minor: int,
    tax_withheld_minor: int = 0,
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P10: Clear Payout Hold to Platform Payout Clearing & Tax Withholding."""
    net_minor = gross_amount_minor - tax_withheld_minor
    entries: list[dict[str, Any]] = [
        {
            "account_number": f"user:payout_hold:{user_id}:{currency}",
            "account_type": "LIABILITY",
            "user_id": user_id,
            "amount": gross_amount_minor,  # Debit payout_hold + (clears hold)
            "currency": currency,
        },
        {
            "account_number": f"platform:payout_clearing:{currency}",
            "account_type": "ASSET",
            "amount": -net_minor,  # Credit clearing -
            "currency": currency,
        },
    ]

    if tax_withheld_minor > 0:
        entries.append({
            "account_number": f"platform:tax_withholding_payable:{currency}",
            "account_type": "LIABILITY",
            "amount": -tax_withheld_minor,  # Credit tax payable -
            "currency": currency,
        })

    return await post_journal_transaction(
        session,
        transaction_type="PAYOUT_PAID",
        reference_type="PAYOUT",
        reference_id=str(payout_id),
        idempotency_key=f"tx:payout:paid:{payout_id}",
        description=f"Payout settled and paid ({payout_id})",
        entries=entries,
    )


async def post_payout_returned(
    session: AsyncSession,
    *,
    payout_id: uuid.UUID,
    user_id: uuid.UUID,
    amount_minor: int,
    reason: str = "rejected",
    currency: str = "BDT",
) -> tuple[JournalTransaction, bool]:
    """P11: Return funds from Payout Hold back to User Available."""
    return await post_journal_transaction(
        session,
        transaction_type="PAYOUT_RETURNED",
        reference_type="PAYOUT",
        reference_id=str(payout_id),
        idempotency_key=f"tx:payout:returned:{payout_id}:{reason}",
        description=f"Payout {reason} - funds returned to wallet ({payout_id})",
        entries=[
            {
                "account_number": f"user:payout_hold:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": amount_minor,  # Debit payout_hold + (clears hold)
                "currency": currency,
            },
            {
                "account_number": f"user:available:{user_id}:{currency}",
                "account_type": "LIABILITY",
                "user_id": user_id,
                "amount": -amount_minor,  # Credit available - (restores available)
                "currency": currency,
            },
        ],
    )


