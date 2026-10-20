"""Pydantic schemas for the tickets domain (§21, ADR 0016)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=64)
    severity: str = Field(default="MEDIUM", pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW)$")
    description: str = Field(min_length=5)
    external_user_id: str | None = Field(default=None, max_length=255)
    system_diagnostics: dict[str, Any] = Field(default_factory=dict)


class PortalTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_slug: str = Field(min_length=2, max_length=64, pattern=r"^(pulsepos|healora)$")
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=64)
    severity: str = Field(default="MEDIUM", pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW)$")
    description: str = Field(min_length=5)
    system_diagnostics: dict[str, Any] = Field(default_factory=dict)


class ProductTicketMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    is_internal_note: bool = False
    sender_name: str | None = Field(default=None, max_length=255)


class ProductTicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(
        default=None,
        pattern=r"^(NEW|TRIAGED|INVESTIGATING|FIX_IN_PROGRESS|RESOLVED|CLOSED)$",
    )
    severity: str | None = Field(default=None, pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW)$")
    assigned_agent_id: uuid.UUID | None = None
    resolution_summary: str | None = None


class ProductTicketResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_summary: str = Field(min_length=3)


class ProductTicketAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    created_at: datetime


class ProductTicketMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_type: str
    sender_user_id: uuid.UUID | None = None
    sender_name: str
    body: str
    is_internal_note: bool
    created_at: datetime
    attachments: list[ProductTicketAttachmentOut] = Field(default_factory=list)


class ProductTicketAuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    action: str
    metadata_json: dict[str, Any]
    created_at: datetime


class ProductTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_number: str
    product_id: uuid.UUID
    product_slug: str | None = None
    external_user_id: str | None = None
    category: str
    severity: str
    status: str
    title: str
    description: str
    system_diagnostics: dict[str, Any]
    assigned_agent_id: uuid.UUID | None = None
    resolution_summary: str | None = None
    sla_due_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ProductTicketMessageOut] = Field(default_factory=list)
    audit_logs: list[ProductTicketAuditLogOut] = Field(default_factory=list)
