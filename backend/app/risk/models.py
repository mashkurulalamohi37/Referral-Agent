"""Risk signals and case models (§14, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey


class RiskSignal(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "risk_signals"

    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # EMAIL | PHONE | IP | IP_PREFIX | DEVICE | PAYMENT_FP | CHARGEBACK
    value_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, index=True)
    product_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)


class RiskCase(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "risk_cases"

    subject_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referral_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attributions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(
        String(32), default="MEDIUM", nullable=False, index=True
    )  # MEDIUM | HIGH | BLOCKED
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="OPEN", nullable=False, index=True
    )  # OPEN | CLEARED | REJECTED | BLOCKED
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
