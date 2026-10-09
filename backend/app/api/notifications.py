"""In-app notifications and preferences endpoints (§16, §20)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.identity.models import User
from app.notifications import service as notif_service

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict]:
    """Returns in-app notifications for authenticated user."""
    notifs = await notif_service.get_user_notifications(session, user_id=user.id)
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "status": n.status,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Marks an in-app notification as read."""
    notif = await notif_service.mark_notification_read(
        session,
        notification_id=notification_id,
        user_id=user.id,
    )
    return {"id": str(notif.id), "status": notif.status}
