"""Risk review and case investigation endpoints (§14, §20)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, require_roles
from app.identity.models import User
from app.risk import service as risk_service

router = APIRouter(prefix="/v1/risk", tags=["risk"])


class DecideRiskCaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str  # CLEARED | REJECTED | BLOCKED
    note: str


@router.get("/cases")
async def list_risk_cases(
    admin_user: Annotated[User, Depends(require_roles("RISK_ANALYST", "ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str = "OPEN",
) -> list[dict]:
    """Lists risk cases for review."""
    cases = await risk_service.get_risk_cases(session, status=status)
    return [
        {
            "id": str(c.id),
            "subject_user_id": str(c.subject_user_id),
            "referral_id": str(c.referral_id) if c.referral_id else None,
            "level": c.level,
            "score": c.score,
            "reasons": c.reasons,
            "status": c.status,
            "notes": c.notes,
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]


@router.post("/cases/{case_id}/decide")
async def decide_case(
    case_id: uuid.UUID,
    payload: DecideRiskCaseBody,
    admin_user: Annotated[User, Depends(require_roles("RISK_ANALYST", "ADMIN", "SUPER_ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Records an audited risk decision on an open fraud case."""
    risk_case = await risk_service.decide_risk_case(
        session,
        case_id=case_id,
        actor_id=admin_user.id,
        decision=payload.decision,
        note=payload.note,
    )
    return {
        "id": str(risk_case.id),
        "status": risk_case.status,
        "decided_by": str(risk_case.decided_by),
    }
