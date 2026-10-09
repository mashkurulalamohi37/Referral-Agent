"""Commission engine models: rules, calculation snapshots, commissions (§9, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core import clock
from app.core.db import Base, Timestamps, UUIDPrimaryKey

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class CommissionRule(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "commission_rules"

    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    plan_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    partner_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    partner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    billing_reason: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    commission_type: Mapped[str] = mapped_column(String(32), default="PERCENTAGE", nullable=False)
    rate_bps: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)  # 1000 = 10.00%
    fixed_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tier_schedule: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    min_net_paid_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    max_commission_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    eligible_months_from_conversion: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    max_payments_per_referral: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_split: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=lambda: {"WALLET": 100}, nullable=False)
    confirmation_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(default=clock.now, nullable=False, index=True)
    effective_until: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)


class Commission(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "commissions"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commission_rules.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    attribution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attributions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    earned_at: Mapped[datetime] = mapped_column(default=clock.now, nullable=False, index=True)
    confirmation_due_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    calculation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    __table_args__ = (
        Index(
            "ix_commissions_product_payment_unique",
            product_id,
            payment_id,
            unique=True,
        ),
    )
