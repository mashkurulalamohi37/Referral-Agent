"""Pydantic models for Referral & Commission SDK requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class Signals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ip: str | None = None
    email: str | None = None
    phone: str | None = None
    device_id: str | None = None
    payment_fingerprint: str | None = None


class AttributionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_user_id: str
    registered_at: datetime
    referral_code: str | None = None
    attribution_token: str | None = None
    signals: Signals | None = None


class AttributionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    attribution_id: str
    status: str
    referrer_code: str | None = None
    source: str


class CreditBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    spendable_minor: int
    credit_only_minor: int
    available_minor: int
    currency: str


class CreditReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_user_id: str
    currency: str = "BDT"
    requested_amount: int = Field(gt=0)
    order_ref: str
    idempotency_key: str


class CreditReservationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reservation_id: str
    order_ref: str
    currency: str
    requested_amount: int
    reserved_amount: int
    from_credit_only: int
    from_available: int
    state: str
    expires_at: str


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    schema_version: int = 1
    occurred_at: str
    data: dict[str, Any]


class TicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=64)
    severity: str = Field(default="MEDIUM", pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW)$")
    description: str = Field(min_length=5)
    external_user_id: str | None = None
    system_diagnostics: dict[str, Any] = Field(default_factory=dict)


class TicketMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    sender_name: str | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    ticket_number: str
    product_id: str
    external_user_id: str | None = None
    category: str
    severity: str
    status: str
    title: str
    description: str
    system_diagnostics: dict[str, Any] = Field(default_factory=dict)
    assigned_agent_id: str | None = None
    resolution_summary: str | None = None
    sla_due_at: str | None = None
    created_at: str
    updated_at: str
    messages: list[dict[str, Any]] = Field(default_factory=list)


class TicketMessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    ticket_id: str
    sender_type: str
    sender_name: str
    body: str
    created_at: str

