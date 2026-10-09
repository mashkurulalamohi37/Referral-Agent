"""Notification templating and transactional outbox service (§16, ADR 0006)."""

from __future__ import annotations

import re
import uuid
from typing import Any

try:
    from jinja2.sandbox import SandboxedEnvironment
    _sandboxed_env = SandboxedEnvironment(autoescape=True)
except ImportError:
    _sandboxed_env = None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import ErrorCode, PlatformError
from app.events import service as events_service
from app.notifications.models import Notification, NotificationTemplate


def render_sandboxed_template(template_str: str, context: dict[str, Any]) -> str:
    """Renders template inside SandboxedEnvironment if available or safe regex replacement."""
    if _sandboxed_env is not None:
        template = _sandboxed_env.from_string(template_str)
        return template.render(**context)

    # Safe regex replacement for {{ var }}
    def _repl(match: re.Match) -> str:
        key = match.group(1).strip()
        return str(context.get(key, f"{{{{ {key} }}}}"))

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", _repl, template_str)


DEFAULT_TEMPLATES = {
    ("referral.attributed", "IN_APP", "en"): (
        "New Referral Attributed!",
        "A new customer was successfully attributed to your referral code.",
    ),
    ("commission.earned", "IN_APP", "en"): (
        "Commission Earned (Pending)",
        "You earned ৳{{ amount_bdt }} in commission! It is currently pending confirmation.",
    ),
    ("commission.available", "IN_APP", "en"): (
        "Commission Available!",
        "৳{{ amount_bdt }} in commission is now available in your wallet to withdraw or spend.",
    ),
    ("payout.approved", "IN_APP", "en"): (
        "Payout Approved",
        "Your payout request for ৳{{ amount_bdt }} has been approved and is being processed.",
    ),
    ("payout.paid", "IN_APP", "en"): (
        "Payout Sent!",
        "Your payout of ৳{{ amount_bdt }} has been transferred via {{ method }}.",
    ),
}


async def send_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    event_key: str,
    context: dict[str, Any],
    channel: str = "IN_APP",
    locale: str = "en",
) -> tuple[Notification, Any]:
    """Writes a notification and outbox record in a single DB transaction (§16)."""
    # 1. Look for template
    stmt = select(NotificationTemplate).where(
        NotificationTemplate.event_key == event_key,
        NotificationTemplate.channel == channel,
        NotificationTemplate.locale == locale,
        NotificationTemplate.active.is_(True),
    )
    res = await session.execute(stmt)
    tmpl = res.scalar_one_or_none()

    if tmpl:
        title = render_sandboxed_template(tmpl.subject, context)
        message = render_sandboxed_template(tmpl.body, context)
        tmpl_id = tmpl.id
    else:
        # Fallback to default copy
        default_pair = DEFAULT_TEMPLATES.get((event_key, channel, locale)) or (
            event_key.replace(".", " ").title(),
            f"Notification regarding {event_key}",
        )
        title = render_sandboxed_template(default_pair[0], context)
        message = render_sandboxed_template(default_pair[1], context)
        tmpl_id = None

    notif = Notification(
        user_id=user_id,
        category="TRANSACTIONAL",
        channel=channel,
        template_id=tmpl_id,
        title=title,
        message=message,
        context_json=context,
        status="SENT" if channel == "IN_APP" else "QUEUED",
    )
    session.add(notif)
    await session.flush()

    # Outbox message for worker dispatch via events_service
    outbox_entry = await events_service.record_outbox_message(
        session,
        aggregate_type="notification",
        aggregate_id=notif.id,
        event_type=f"notification.{channel.lower()}",
        payload={
            "notification_id": str(notif.id),
            "user_id": str(user_id),
            "channel": channel,
            "title": title,
            "message": message,
            "event_key": event_key,
        },
        status="PENDING",
    )

    return notif, outbox_entry


async def get_user_notifications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[Notification]:
    """Fetches in-app notifications for the user."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def mark_notification_read(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification:
    """Marks a notification as read."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).with_for_update()
    res = await session.execute(stmt)
    notif = res.scalar_one_or_none()
    if not notif:
        raise PlatformError(ErrorCode.NOT_FOUND, f"Notification not found: {notification_id}")

    notif.status = "READ"
    notif.read_at = clock.now()
    await session.flush()
    return notif
