"""Reports, metrics and product reconciliation endpoints (§17.2, §17.3, ADR 0017)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_api_client, get_db_session, require_roles
from app.catalog.models import ApiClient
from app.identity.models import User
from app.reporting import service as reporting_service

router = APIRouter(prefix="/v1", tags=["reporting"])


class PaymentReconciliationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    amount_net_paid: int


class PaymentReconciliationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_date: date
    payments: list[PaymentReconciliationItem]


@router.get("/reports/dashboard")
async def get_dashboard_summary(
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "SUPER_ADMIN", "FINANCE_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: uuid.UUID | None = None,
) -> dict:
    """Returns aggregated executive dashboard metrics."""
    return await reporting_service.get_admin_dashboard_metrics(
        session,
        product_id=product_id,
    )


@router.get("/reports/commissions/csv")
async def export_commissions_csv(
    admin_user: Annotated[User, Depends(require_roles("ADMIN", "SUPER_ADMIN", "FINANCE_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: uuid.UUID | None = None,
) -> Response:
    """Exports commissions report in CSV format."""
    csv_str = await reporting_service.export_commissions_csv(session, product_id=product_id)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commissions_report.csv"},
    )


@router.post("/reconciliation/payments")
async def submit_payment_reconciliation(
    payload: PaymentReconciliationRequest,
    client: Annotated[ApiClient, Depends(get_authenticated_api_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Daily payment list from connected products to detect missed events (ADR 0017, §20)."""
    run = await reporting_service.process_daily_payment_reconciliation(
        session,
        product_id=client.product_id,
        business_date=payload.business_date,
        payments=[p.model_dump() for p in payload.payments],
    )
    return {
        "run_id": str(run.id),
        "business_date": run.business_date.isoformat(),
        "submitted_count": run.submitted_count,
        "matched_count": run.matched_count,
        "missing_count": run.missing_count,
        "mismatch_count": run.mismatch_count,
        "details": run.details_json,
    }
