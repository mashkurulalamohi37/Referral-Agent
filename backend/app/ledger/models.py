"""Double-entry ledger models (§10, ADR 0007, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey


class LedgerAccount(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "ledger_accounts"

    account_number: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    entries: Mapped[list[LedgerEntry]] = relationship("LedgerEntry", back_populates="account")


class JournalTransaction(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "journal_transactions"

    transaction_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(default=clock.now, nullable=False, index=True)

    entries: Mapped[list[LedgerEntry]] = relationship(
        "LedgerEntry", back_populates="transaction", cascade="all, delete-orphan"
    )


class LedgerEntry(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "ledger_entries"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ledger_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)

    transaction: Mapped[JournalTransaction] = relationship("JournalTransaction", back_populates="entries")
    account: Mapped[LedgerAccount] = relationship("LedgerAccount", back_populates="entries")
