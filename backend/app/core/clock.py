"""The only source of "now" in the codebase (ADR 0003). Tests replace it with `frozen()`."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated

from pydantic import AfterValidator


def _system_now() -> datetime:
    return datetime.now(UTC)


_source: Callable[[], datetime] = _system_now


def now() -> datetime:
    return _source()


def ensure_utc(value: datetime) -> datetime:
    """Reject naive datetimes; normalise aware ones to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "datetime must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
"""Pydantic field type: aware datetime, stored and compared in UTC."""


class FrozenClock:
    def __init__(self, at: datetime) -> None:
        self.current = ensure_utc(at)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta

    def set(self, at: datetime) -> None:
        self.current = ensure_utc(at)


@contextmanager
def frozen(at: datetime) -> Iterator[FrozenClock]:
    global _source  # noqa: PLW0603 - deliberate test hook
    clock = FrozenClock(at)
    previous = _source
    _source = clock
    try:
        yield clock
    finally:
        _source = previous
