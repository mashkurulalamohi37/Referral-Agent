"""Catalog models: products, plans, API clients, product accounts (§21, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey



class Product(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    signup_url: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_redirect_hosts: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    attribution_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    attribution_grace_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    conversion_window_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    refund_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    confirmation_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    referrer_visibility: Mapped[str] = mapped_column(String(32), default="MASKED", nullable=False)
    sensitive_category: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepts_cross_product_credit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credit_max_invoice_pct: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    referral_code_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    theme: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outbound_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    outbound_signing_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    plans: Mapped[list[Plan]] = relationship(
        "Plan",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    api_clients: Mapped[list[ApiClient]] = relationship(
        "ApiClient",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    product_accounts: Mapped[list[ProductAccount]] = relationship(
        "ProductAccount",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class Plan(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "plans"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    product: Mapped[Product] = relationship("Product", back_populates="plans")

    __table_args__ = (
        UniqueConstraint("product_id", "plan_code", name="uq_plans_product_id_plan_code"),
    )


class ApiClient(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "api_clients"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    product: Mapped[Product] = relationship("Product", back_populates="api_clients")
    secrets: Mapped[list[ApiClientSecret]] = relationship(
        "ApiClientSecret",
        back_populates="api_client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ApiClientSecret(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "api_client_secrets"

    api_client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("api_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secret_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    signing_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    api_client: Mapped[ApiClient] = relationship("ApiClient", back_populates="secrets")


class ProductAccount(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "product_accounts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    account_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    product: Mapped[Product] = relationship("Product", back_populates="product_accounts")
    user: Mapped[Any | None] = relationship("User", back_populates="product_accounts")

    __table_args__ = (
        UniqueConstraint(
            "product_id", "external_user_id", name="uq_product_accounts_product_external_user"
        ),
    )

