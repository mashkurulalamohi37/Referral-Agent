"""Referral models: codes, clicks, attribution records (§6, §7, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey

# JSON column fallback for SQLite testing
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ReferralCode(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "referral_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    is_vanity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    attribution_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    clicks: Mapped[list[ReferralClick]] = relationship(
        "ReferralClick",
        back_populates="referral_code",
        cascade="all, delete-orphan",
    )
    attributions: Mapped[list[Attribution]] = relationship(
        "Attribution",
        back_populates="referral_code",
    )

    __table_args__ = (
        Index(
            "ix_referral_codes_code_upper_unique",
            func.upper(code),
            unique=True,
        ),
    )


class ReferralClick(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "referral_clicks"

    code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("referral_codes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    user_agent_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    referer_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    campaign: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(64), nullable=True)

    referral_code: Mapped[ReferralCode] = relationship("ReferralCode", back_populates="clicks")


class Attribution(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "attributions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("referral_codes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    click_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("referral_clicks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ATTRIBUTED", nullable=False)
    registered_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    signals_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    referral_code: Mapped[ReferralCode] = relationship("ReferralCode", back_populates="attributions")

    __table_args__ = (
        Index(
            "ix_attributions_product_external_unique",
            product_id,
            external_user_id,
            unique=True,
        ),
    )
