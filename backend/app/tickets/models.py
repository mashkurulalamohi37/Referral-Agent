"""Tickets domain models: Product tickets, messages, attachments, and audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core import clock
from app.core.db import Base, CreatedAt, Timestamps, UUIDPrimaryKey

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ProductTicket(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "product_tickets"

    ticket_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    messages: Mapped[list[ProductTicketMessage]] = relationship(
        "ProductTicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ProductTicketMessage.created_at",
    )
    audit_logs: Mapped[list[ProductTicketAuditLog]] = relationship(
        "ProductTicketAuditLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ProductTicketAuditLog.created_at",
    )


class ProductTicketMessage(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "product_ticket_messages"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PRODUCT_CLIENT | SUPPORT_ENGINEER | SYSTEM
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sender_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal_note: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped[ProductTicket] = relationship("ProductTicket", back_populates="messages")
    attachments: Mapped[list[ProductTicketAttachment]] = relationship(
        "ProductTicketAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ProductTicketAttachment(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "product_ticket_attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_ticket_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), default="application/octet-stream", nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    message: Mapped[ProductTicketMessage] = relationship("ProductTicketMessage", back_populates="attachments")


class ProductTicketAuditLog(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "product_ticket_audit_logs"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    ticket: Mapped[ProductTicket] = relationship("ProductTicket", back_populates="audit_logs")
