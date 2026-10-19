"""Administrative management API endpoints (§17, docs/openapi.yaml)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import service as admin_service
from app.api.deps import (
    get_db_session,
    require_roles,
)
from app.events import service as event_service
from app.identity.models import User
from app.payouts import service as payouts_service
from app.reporting import service as reporting_service

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get(
    "/audit-logs",
    response_model=dict[str, Any],
    summary="Admin: List immutable audit trail records (§17.4)",
)
async def list_audit_logs_endpoint(
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "RISK_ANALYST"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    logs = await admin_service.list_audit_logs(
        session,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        action=action,
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(log.id),
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "actor_email": log.actor_email or "system",
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "diff_json": log.diff_json,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get(
    "/events",
    response_model=dict[str, Any],
    summary="Admin: Inspect live inbound event stream (§17.1)",
)
async def list_events_endpoint(
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    events = await event_service.list_inbound_events(
        session,
        product_id=product_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(evt.id),
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "product_id": str(evt.product_id),
                "status": evt.status,
                "occurred_at": evt.occurred_at.isoformat(),
                "created_at": evt.created_at.isoformat(),
            }
            for evt in events
        ],
    }


@router.post(
    "/events/{event_id}/replay",
    response_model=dict[str, Any],
    summary="Admin: Idempotently replay an inbound or dead-letter event (§8.4, §17.1)",
)
async def replay_event_endpoint(
    event_id: uuid.UUID,
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    replayed = await event_service.replay_inbound_event(session, event_id=event_id)
    return {
        "success": True,
        "data": {
            "id": str(replayed.id),
            "event_id": replayed.event_id,
            "status": replayed.status,
            "processed_at": replayed.processed_at.isoformat() if replayed.processed_at else None,
        },
    }


@router.get(
    "/payouts",
    response_model=dict[str, Any],
    summary="Admin: Review partner payout disbursement requests (§13)",
)
async def list_admin_payouts_endpoint(
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "FINANCE_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    state: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    payouts = await payouts_service.list_payouts(
        session,
        state=state,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "amount_minor": p.amount_minor,
                "currency": p.currency,
                "net_minor": p.net_minor,
                "state": p.state,
                "provider": p.provider,
                "provider_ref": p.provider_ref,
                "created_at": p.created_at.isoformat(),
            }
            for p in payouts
        ],
    }


@router.get(
    "/reports/dashboard",
    response_model=dict[str, Any],
    summary="Admin: Aggregate operations dashboard metrics (§17.2)",
)
async def get_dashboard_metrics_endpoint(
    admin_user: Annotated[User, Depends(require_roles("SUPER_ADMIN", "ADMIN", "FINANCE_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: uuid.UUID | None = Query(default=None),
) -> dict[str, Any]:
    metrics = await reporting_service.get_admin_dashboard_metrics(session, product_id=product_id)
    return {
        "success": True,
        "data": metrics,
    }
