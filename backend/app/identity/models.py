"""Identity models: users, roles, refresh tokens, handoff tokens, OTP (§21, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), default="Asia/Dhaka", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    kyc_status: Mapped[str] = mapped_column(String(32), default="NONE", nullable=False)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    roles: Mapped[list[UserRole]] = relationship(
        "UserRole",
        back_populates="user",
        foreign_keys="[UserRole.user_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    product_accounts: Mapped[list[Any]] = relationship(
        "ProductAccount",
        back_populates="user",
    )


    __table_args__ = (
        Index(
            "ix_users_email_lower_unique",
            func.lower(email),
            unique=True,
            postgresql_where=(email.isnot(None) & deleted_at.is_(None)),
        ),
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="roles", foreign_keys=[user_id])


class RefreshToken(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, nullable=False)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")


class AuthHandoffToken(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "auth_handoff_tokens"

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class OTPChallenge(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "otp_challenges"

    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(nullable=True)
