"""Notification and outbox models (§16, docs/erd.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class NotificationTemplate(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "notification_templates"

    event_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # IN_APP | EMAIL | PUSH
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)  # en | bn
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(64), default="TRANSACTIONAL", nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="IN_APP", nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="QUEUED", nullable=False, index=True
    )  # QUEUED | SENT | FAILED | READ
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)

