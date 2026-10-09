"""System tasks. Domain tasks live next to their module and follow the same pattern:
take IDs, call `runtime.run_async(service_fn)`, contain no business logic."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, context
from app.worker import runtime
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


HEARTBEAT_KEY = "system:heartbeat"


async def _database_time(session: AsyncSession) -> str:
    value = (await session.execute(text("SELECT now()"))).scalar_one()
    # Read by the Beat container's health check: proves beat → broker → worker → DB.
    await runtime.resources().redis.set(HEARTBEAT_KEY, clock.now().isoformat(), ex=600)
    return str(value)


@celery_app.task(name="system.heartbeat")
def heartbeat() -> str:
    """Beat → worker → database round trip; proves the ADR 0002 runtime end to end."""
    context.clear()
    context.bind(operation="system.heartbeat")
    db_now = runtime.run_async(_database_time)
    logger.info("heartbeat", extra={"db_now": db_now, "worker_now": clock.now().isoformat()})
    return db_now
