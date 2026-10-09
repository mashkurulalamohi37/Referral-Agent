"""Credits and reservation models (§11, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.core.db import Base, Timestamps, UUIDPrimaryKey


class CreditReservation(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "credit_reservations"
    __table_args__ = (
        UniqueConstraint("product_id", "idempotency_key", name="uq_credit_reservation_idempotency"),
        Index("ix_credit_reservations_user_state", "user_id", "state"),
        Index("ix_credit_reservations_expires", "state", "expires_at"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    product_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    requested_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_credit_only_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    from_available_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    captured_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    late_captured_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    state: Mapped[str] = mapped_column(
        String(32), default="RESERVED", nullable=False, index=True
    )  # RESERVED | CAPTURED | PARTIALLY_CAPTURED | RELEASED | EXPIRED | LATE_CAPTURED
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    refunds: Mapped[list[CreditRefund]] = relationship("CreditRefund", back_populates="reservation")


class CreditRefund(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "credit_refunds"
    __table_args__ = (
        UniqueConstraint("product_id", "idempotency_key", name="uq_credit_refund_idempotency"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("credit_reservations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    journal_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_transactions.id", ondelete="SET NULL"), nullable=True
    )

    reservation: Mapped[CreditReservation] = relationship("CreditReservation", back_populates="refunds")
