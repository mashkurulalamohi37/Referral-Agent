"""Tickets API endpoints for connected client products and operations desk (§20, ADR 0016)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_authenticated_api_client,
    get_current_user,
    get_db_session,
    require_roles,
)
from app.catalog import service as catalog_service
from app.catalog.models import ApiClient
from app.core.errors import ErrorCode, PlatformError
from app.identity.models import User
from app.tickets import service as tickets_service
from app.tickets.schemas import (
    ProductTicketCreate,
    ProductTicketMessageCreate,
    ProductTicketMessageOut,
    ProductTicketOut,
    ProductTicketResolve,
    ProductTicketUpdate,
)

router = APIRouter(tags=["tickets"])


# ---------------------------------------------------------------- Products / Client API


@router.post(
    "/v1/products/{product_slug}/tickets",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, Any],
)
async def submit_product_ticket(
    product_slug: str,
    payload: ProductTicketCreate,
    api_client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Allows connected products (PulsePOS, Healora) to programmatically submit tickets and bug reports."""
    product = await catalog_service.get_product_by_slug(session, product_slug)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_slug}' not found")

    # Guard: API client may only submit tickets for its own product
    if api_client.product_id != product.id:
        raise PlatformError(
            ErrorCode.PERMISSION_DENIED,
            "API client credentials belong to a different product",
        )

    ticket = await tickets_service.create_product_ticket(
        session,
        product_slug=product_slug,
        data=payload,
    )
    return {
        "success": True,
        "data": ProductTicketOut.model_validate(ticket).model_dump(mode="json"),
    }


@router.get(
    "/v1/products/{product_slug}/tickets/{ticket_number}",
    response_model=dict[str, Any],
)
async def get_product_ticket_status(
    product_slug: str,
    ticket_number: str,
    api_client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Allows connected products to inspect status and public messages of an existing ticket."""
    product = await catalog_service.get_product_by_slug(session, product_slug)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_slug}' not found")

    if api_client.product_id != product.id:
        raise PlatformError(ErrorCode.PERMISSION_DENIED, "Access denied to product tickets")

    ticket = await tickets_service.get_ticket_by_number(
        session, ticket_number, include_internal_notes=False
    )
    if not ticket or ticket.product_id != product.id:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_number}' not found")

    return {
        "success": True,
        "data": ProductTicketOut.model_validate(ticket).model_dump(mode="json"),
    }


@router.post(
    "/v1/products/{product_slug}/tickets/{ticket_number}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, Any],
)
async def reply_product_ticket(
    product_slug: str,
    ticket_number: str,
    payload: ProductTicketMessageCreate,
    api_client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Allows connected products to append follow-up messages or log data to a ticket."""
    product = await catalog_service.get_product_by_slug(session, product_slug)
    if not product:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Product '{product_slug}' not found")

    if api_client.product_id != product.id:
        raise PlatformError(ErrorCode.PERMISSION_DENIED, "Access denied to product tickets")

    ticket = await tickets_service.get_ticket_by_number(
        session, ticket_number, include_internal_notes=False
    )
    if not ticket or ticket.product_id != product.id:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_number}' not found")

    msg = await tickets_service.add_ticket_message(
        session,
        ticket_id=ticket.id,
        body=payload.body,
        sender_type="PRODUCT_CLIENT",
        sender_name=payload.sender_name or product.name,
        is_internal_note=False,
    )
    return {
        "success": True,
        "data": ProductTicketMessageOut.model_validate(msg).model_dump(mode="json"),
    }


# ---------------------------------------------------------------- Admin Operations Desk


@router.get("/v1/admin/tickets", response_model=dict[str, Any])
async def list_admin_tickets(
    user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "SUPPORT", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_slug: str | None = None,
    product_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    assigned_agent_id: uuid.UUID | None = None,
    sla_breached: bool | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Operations desk queue listing tickets with multi-product and SLA filters."""
    tickets = await tickets_service.list_tickets(
        session,
        product_id=product_id,
        product_slug=product_slug,
        status=status,
        severity=severity,
        category=category,
        assigned_agent_id=assigned_agent_id,
        sla_breached=sla_breached,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [ProductTicketOut.model_validate(t).model_dump(mode="json") for t in tickets],
    }


@router.get("/v1/admin/tickets/{ticket_id}", response_model=dict[str, Any])
async def get_admin_ticket(
    ticket_id: uuid.UUID,
    user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "SUPPORT", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Retrieves full ticket details including private internal engineering notes."""
    ticket = await tickets_service.get_ticket_by_id(session, ticket_id, include_internal_notes=True)
    if not ticket:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_id}' not found")

    return {
        "success": True,
        "data": ProductTicketOut.model_validate(ticket).model_dump(mode="json"),
    }


@router.post(
    "/v1/admin/tickets/{ticket_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, Any],
)
async def add_admin_ticket_message(
    ticket_id: uuid.UUID,
    payload: ProductTicketMessageCreate,
    user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "SUPPORT", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Allows support engineers to reply to client products or add private internal notes."""
    msg = await tickets_service.add_ticket_message(
        session,
        ticket_id=ticket_id,
        body=payload.body,
        sender_type="SUPPORT_ENGINEER",
        sender_user_id=user.id,
        sender_name=user.display_name or "Support Engineer",
        is_internal_note=payload.is_internal_note,
    )
    return {
        "success": True,
        "data": ProductTicketMessageOut.model_validate(msg).model_dump(mode="json"),
    }


@router.patch("/v1/admin/tickets/{ticket_id}", response_model=dict[str, Any])
async def update_admin_ticket(
    ticket_id: uuid.UUID,
    payload: ProductTicketUpdate,
    user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "SUPPORT", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Updates ticket status, severity, or reassigns support engineer."""
    ticket = await tickets_service.get_ticket_by_id(session, ticket_id)
    if not ticket:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Ticket '{ticket_id}' not found")

    if payload.assigned_agent_id is not None:
        await tickets_service.assign_ticket(
            session,
            ticket_id=ticket.id,
            agent_id=payload.assigned_agent_id,
            actor_id=user.id,
        )

    if payload.status is not None:
        await tickets_service.update_ticket_status(
            session,
            ticket_id=ticket.id,
            new_status=payload.status,
            actor_id=user.id,
            resolution_summary=payload.resolution_summary,
        )

    updated = await tickets_service.get_ticket_by_id(session, ticket_id, include_internal_notes=True)
    return {
        "success": True,
        "data": ProductTicketOut.model_validate(updated).model_dump(mode="json"),
    }


@router.post("/v1/admin/tickets/{ticket_id}/resolve", response_model=dict[str, Any])
async def resolve_admin_ticket(
    ticket_id: uuid.UUID,
    payload: ProductTicketResolve,
    user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "SUPPORT", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Marks a ticket RESOLVED with an official resolution summary and emits outbox webhook."""
    ticket = await tickets_service.update_ticket_status(
        session,
        ticket_id=ticket_id,
        new_status="RESOLVED",
        actor_id=user.id,
        resolution_summary=payload.resolution_summary,
    )
    full = await tickets_service.get_ticket_by_id(session, ticket.id, include_internal_notes=True)
    return {
        "success": True,
        "data": ProductTicketOut.model_validate(full).model_dump(mode="json"),
    }
