"""Per-request / per-task context carried into every log line (§22.2)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

LOG_CONTEXT_FIELDS = (
    "request_id",
    "api_client_id",
    "user_id",
    "product_id",
    "event_id",
    "operation",
)

_log_context: ContextVar[dict[str, Any] | None] = ContextVar("log_context", default=None)


def get_log_context() -> dict[str, Any]:
    return dict(_log_context.get() or {})


def bind(**values: Any) -> None:
    """Add fields to the current context (copy-on-write, so concurrent tasks don't share)."""
    current = dict(_log_context.get() or {})
    current.update({k: v for k, v in values.items() if v is not None})
    _log_context.set(current)


def clear() -> None:
    _log_context.set(None)


def request_id() -> str:
    value = get_log_context().get("request_id")
    return str(value) if value else "-"
