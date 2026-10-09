"""Payout and approval models (§13, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey


class PayoutMethod(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "payout_methods"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # bkash | nagad | bank_transfer
    masked_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    details_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    payouts: Mapped[list[Payout]] = relationship("Payout", back_populates="payout_method")


class Payout(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "payouts"
    __table_args__ = (
        Index("ix_payouts_user_state", "user_id", "state"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payout_method_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payout_methods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Gross
    tax_withheld_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    net_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), default="REQUESTED", nullable=False, index=True
    )  # REQUESTED | UNDER_REVIEW | APPROVED | PROCESSING | PAID | REJECTED | CANCELLED | FAILED | RETURNED
    provider: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    payout_method: Mapped[PayoutMethod] = relationship("PayoutMethod", back_populates="payouts")


class Approval(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint("approved_by <> requested_by", name="ck_approvals_maker_checker_distinct"),
    )

    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # payout | ledger_adjustment | rule_activation
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # APPROVED | REJECTED
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
