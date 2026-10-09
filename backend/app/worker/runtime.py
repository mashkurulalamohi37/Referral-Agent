"""Async runtime for Celery worker processes (ADR 0002).

Each prefork child owns one event loop and one async engine for its whole life. Tasks are thin
sync wrappers that call `run_async(...)`, which runs a coroutine on that loop with a fresh
session. All business logic stays in async `service.py` functions shared with the API.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.resources import Resources

logger = logging.getLogger(__name__)

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_resources: Resources | None = None


def init_process() -> None:
    """Called from Celery's worker_process_init signal (and lazily by run_async)."""
    global _loop, _resources  # noqa: PLW0603 - one runtime per worker process
    if _loop is not None:
        return
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _resources = Resources.create(get_settings())
    logger.info("worker runtime initialised")


def shutdown_process() -> None:
    global _loop, _resources  # noqa: PLW0603
    if _loop is None:
        return
    if _resources is not None:
        _loop.run_until_complete(_resources.close())
    _loop.close()
    _loop, _resources = None, None


def resources() -> Resources:
    init_process()
    assert _resources is not None
    return _resources


def run_async(fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run `fn(session)` in one transaction on the process loop: commit on success."""
    res = resources()
    assert _loop is not None

    async def _unit_of_work() -> T:
        async with res.session_factory() as session:
            try:
                result = await fn(session)
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
            return result

    return _loop.run_until_complete(_unit_of_work())
