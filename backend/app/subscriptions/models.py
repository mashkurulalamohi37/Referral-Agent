"""Subscription and Payment derived fact models (§8.3, §21, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Subscription(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "subscriptions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    __table_args__ = (
        Index(
            "ix_subscriptions_product_sub_unique",
            product_id,
            subscription_id,
            unique=True,
        ),
    )


class PaymentFact(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "payment_facts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_reason: Mapped[str] = mapped_column(String(32), default="initial", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    amount_gross: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tax_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    credit_applied_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    credit_reservation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    amount_net_paid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    payment_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "ix_payment_facts_product_payment_unique",
            product_id,
            payment_id,
            unique=True,
        ),
    )


class RefundFact(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "refund_facts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refund_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    amount_refunded: Mapped[int] = mapped_column(BigInteger, nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "ix_refund_facts_product_refund_unique",
            product_id,
            refund_id,
            unique=True,
        ),
    )
