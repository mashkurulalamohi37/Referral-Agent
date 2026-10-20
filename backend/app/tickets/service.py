"""Tickets public domain service interface (§3 module boundaries, ADR 0006)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog import service as catalog_service
from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.events import service as events_service
from app.tickets.models import (
    ProductTicket,
    ProductTicketAttachment,
    ProductTicketAuditLog,
    ProductTicketMessage,
)
from app.tickets.privacy import validate_product_ticket_privacy
from app.tickets.schemas import ProductTicketCreate

SLA_HOURS = {
    "CRITICAL": 2,
    "HIGH": 8,
    "MEDIUM": 24,
    "LOW": 72,
}

VALID_STATUSES = {
    "NEW",
    "TRIAGED",
    "INVESTIGATING",
    "FIX_IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
}


def calculate_sla_due(severity: str, from_time: datetime | None = None) -> datetime:
    """Calculates SLA expiration timestamp based on ticket severity."""
    base = from_time or clock.now()
    hours = SLA_HOURS.get(severity.upper(), 24)
    return base + timedelta(hours=hours)


async def generate_ticket_number(session: AsyncSession, product_slug: str) -> str:
    """Generates sequential, readable ticket code per product (e.g. TKT-PULSEPOS-0001)."""
    prefix = f"TKT-{product_slug.upper()}-"
    stmt = (
        select(func.count(ProductTicket.id))
        .join_from(ProductTicket, select(ProductTicket.id).subquery(), isouter=True)  # count all
    )
    # Simple count query for tickets with this prefix
    count_stmt = select(func.count()).select_from(ProductTicket).where(ProductTicket.ticket_number.like(f"{prefix}%"))
    count = (await session.execute(count_stmt)).scalar_one()
    for seq in range(count + 1, count + 100):
        candidate = f"{prefix}{seq:04d}"
        exists_stmt = select(ProductTicket.id).where(ProductTicket.ticket_number == candidate)
        if not (await session.execute(exists_stmt)).scalar_one_or_none():
            return candidate

    # Fallback with uuid suffix if sequence collision
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


async def create_product_ticket(
    session: AsyncSession,
    *,
    product_slug: str,
    data: ProductTicketCreate,
    actor_id: uuid.UUID | None = None,
) -> ProductTicket:
    """Creates a new ticket raised by or for a connected product with privacy checks."""
    product = await catalog_service.get_product_by_slug(session, product_slug)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_slug}' not found")

    # 1. Enforce privacy invariant on sensitive products (e.g. Healora)
    validate_product_ticket_privacy(
        is_sensitive_product=product.sensitive_category,
        title=data.title,
        description=data.description,
        diagnostics=data.system_diagnostics,
    )

    ticket_number = await generate_ticket_number(session, product_slug)
    sla_due_at = calculate_sla_due(data.severity)

    ticket = ProductTicket(
        ticket_number=ticket_number,
        product_id=product.id,
        external_user_id=data.external_user_id,
        category=data.category.upper(),
        severity=data.severity.upper(),
        status="NEW",
        title=data.title,
        description=data.description,
        system_diagnostics=data.system_diagnostics,
        assigned_agent_id=None,
        sla_due_at=sla_due_at,
    )
    session.add(ticket)
    await session.flush()

    # 2. Record audit log
    audit_log = ProductTicketAuditLog(
        ticket_id=ticket.id,
        actor_id=actor_id,
        action="TICKET_CREATED",
        metadata_json={
            "ticket_number": ticket_number,
            "product_slug": product_slug,
            "severity": data.severity,
            "category": data.category,
        },
    )
    session.add(audit_log)

    # 3. Add initial description as first client message
    initial_msg = ProductTicketMessage(
        ticket=ticket,
        sender_type="PRODUCT_CLIENT",
        sender_user_id=actor_id,
        sender_name=data.external_user_id or product.name,
        body=data.description,
        is_internal_note=False,
    )
    session.add(initial_msg)
    await session.flush()

    # 4. Record transactional outbox event
    await events_service.record_outbox_message(
        session,
        aggregate_type="ticket",
        aggregate_id=ticket.id,
        event_type="ticket.created",
        payload={
            "ticket_id": str(ticket.id),
            "ticket_number": ticket_number,
            "product_slug": product_slug,
            "category": ticket.category,
            "severity": ticket.severity,
            "title": ticket.title,
            "created_at": ticket.created_at.isoformat(),
        },
    )

    return ticket


async def get_ticket_by_id(
    session: AsyncSession,
    ticket_id: uuid.UUID,
    *,
    include_internal_notes: bool = True,
) -> ProductTicket | None:
    """Fetches a ticket with its messages and audit logs, optionally filtering internal notes."""
    stmt = (
        select(ProductTicket)
        .options(
            selectinload(ProductTicket.messages).selectinload(ProductTicketMessage.attachments),
            selectinload(ProductTicket.audit_logs),
        )
        .where(ProductTicket.id == ticket_id)
    )
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    if not include_internal_notes:
        session.expunge(ticket)
        ticket.messages = [m for m in ticket.messages if not m.is_internal_note]

    return ticket


async def get_ticket_by_number(
    session: AsyncSession,
    ticket_number: str,
    *,
    include_internal_notes: bool = True,
) -> ProductTicket | None:
    """Fetches a ticket by human-readable ticket number."""
    stmt = (
        select(ProductTicket)
        .options(
            selectinload(ProductTicket.messages).selectinload(ProductTicketMessage.attachments),
            selectinload(ProductTicket.audit_logs),
        )
        .where(ProductTicket.ticket_number == ticket_number.strip().upper())
    )
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None

    if not include_internal_notes:
        session.expunge(ticket)
        ticket.messages = [m for m in ticket.messages if not m.is_internal_note]

    return ticket


async def list_tickets(
    session: AsyncSession,
    *,
    product_id: uuid.UUID | None = None,
    product_slug: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    assigned_agent_id: uuid.UUID | None = None,
    sla_breached: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ProductTicket]:
    """Lists tickets matching operational filters."""
    stmt = (
        select(ProductTicket)
        .options(
            selectinload(ProductTicket.messages),
            selectinload(ProductTicket.audit_logs),
        )
        .order_by(ProductTicket.created_at.desc())
    )

    if product_id:
        stmt = stmt.where(ProductTicket.product_id == product_id)
    elif product_slug:
        product = await catalog_service.get_product_by_slug(session, product_slug)
        if product:
            stmt = stmt.where(ProductTicket.product_id == product.id)
        else:
            return []

    if status:
        stmt = stmt.where(ProductTicket.status == status.upper())
    if severity:
        stmt = stmt.where(ProductTicket.severity == severity.upper())
    if category:
        stmt = stmt.where(ProductTicket.category == category.upper())
    if assigned_agent_id:
        stmt = stmt.where(ProductTicket.assigned_agent_id == assigned_agent_id)

    if sla_breached is True:
        stmt = stmt.where(
            ProductTicket.sla_due_at.isnot(None),
            ProductTicket.sla_due_at < clock.now(),
            ProductTicket.status.notin_(["RESOLVED", "CLOSED"]),
        )

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_tickets_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ProductTicket]:
    """Lists tickets belonging to a specific portal user (excluding internal notes)."""
    target_ext_id = f"user_{user_id}"
    stmt = (
        select(ProductTicket)
        .options(
            selectinload(ProductTicket.messages),
            selectinload(ProductTicket.audit_logs),
        )
        .where(ProductTicket.external_user_id == target_ext_id)
        .order_by(ProductTicket.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    tickets = list(result.scalars().all())
    for t in tickets:
        t.messages = [m for m in t.messages if not m.is_internal_note]
    return tickets


async def add_ticket_message(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    body: str,
    sender_type: str,
    sender_user_id: uuid.UUID | None = None,
    sender_name: str = "",
    is_internal_note: bool = False,
) -> ProductTicketMessage:
    """Adds a message or internal note to a ticket."""
    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_id}' not found")

    if ticket.status == "CLOSED":
        raise PlatformError(ErrorCode.CONFLICT, "Cannot add messages to a closed ticket")

    msg = ProductTicketMessage(
        ticket=ticket,
        sender_type=sender_type,
        sender_user_id=sender_user_id,
        sender_name=sender_name,
        body=body,
        is_internal_note=is_internal_note,
    )
    session.add(msg)
    ticket.updated_at = clock.now()
    await session.flush()

    # Outbox message if this is a public reply visible to the product client
    if not is_internal_note:
        await events_service.record_outbox_message(
            session,
            aggregate_type="ticket",
            aggregate_id=ticket.id,
            event_type="ticket.replied",
            payload={
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "sender_type": sender_type,
                "sender_name": sender_name,
                "created_at": msg.created_at.isoformat(),
            },
        )

    return msg


async def update_ticket_status(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    new_status: str,
    actor_id: uuid.UUID | None = None,
    resolution_summary: str | None = None,
) -> ProductTicket:
    """Transitions ticket status with audit logging and outbox events."""
    normalized_status = new_status.upper().strip()
    if normalized_status not in VALID_STATUSES:
        raise PlatformError(ErrorCode.VALIDATION_ERROR, f"Invalid ticket status: '{new_status}'")

    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_id}' not found")

    old_status = ticket.status
    ticket.status = normalized_status
    now_time = clock.now()
    ticket.updated_at = now_time

    if normalized_status == "RESOLVED":
        ticket.resolved_at = now_time
        if resolution_summary:
            ticket.resolution_summary = resolution_summary
    elif normalized_status == "CLOSED":
        ticket.closed_at = now_time

    audit_log = ProductTicketAuditLog(
        ticket_id=ticket.id,
        actor_id=actor_id,
        action="STATUS_CHANGED",
        metadata_json={
            "old_status": old_status,
            "new_status": normalized_status,
            "resolution_summary": resolution_summary,
        },
    )
    session.add(audit_log)
    await session.flush()

    # Record outbox notification
    await events_service.record_outbox_message(
        session,
        aggregate_type="ticket",
        aggregate_id=ticket.id,
        event_type="ticket.status_changed",
        payload={
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "old_status": old_status,
            "new_status": normalized_status,
            "resolution_summary": resolution_summary,
            "updated_at": now_time.isoformat(),
        },
    )

    return ticket


async def assign_ticket(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    agent_id: uuid.UUID | None,
    actor_id: uuid.UUID | None = None,
) -> ProductTicket:
    """Assigns an operations or support engineer to a ticket."""
    ticket = await get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_id}' not found")

    old_agent = ticket.assigned_agent_id
    ticket.assigned_agent_id = agent_id
    ticket.updated_at = clock.now()

    # Automatically transition from NEW to TRIAGED on assignment
    if ticket.status == "NEW" and agent_id is not None:
        ticket.status = "TRIAGED"

    audit_log = ProductTicketAuditLog(
        ticket_id=ticket.id,
        actor_id=actor_id,
        action="AGENT_ASSIGNED",
        metadata_json={
            "old_agent_id": str(old_agent) if old_agent else None,
            "new_agent_id": str(agent_id) if agent_id else None,
        },
    )
    session.add(audit_log)
    await session.flush()
    return ticket
