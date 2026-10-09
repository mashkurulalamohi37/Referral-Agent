"""HTTP plumbing: request-context middleware, access logging, metrics, error envelope."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import context
from app.core.errors import ErrorCode, PlatformError, error_body
from app.core.ids import uuid7

logger = logging.getLogger("app.http")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0),
)


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


class RequestContextMiddleware:
    """Assigns a request ID, binds log context, writes one access log line, records metrics.

    The access log deliberately omits client IP and query strings (§15: no raw signals, and
    query strings can carry attribution tokens).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, b"x-request-id")
        request_id = incoming if incoming and _REQUEST_ID_RE.match(incoming) else str(uuid7())
        context.clear()
        context.bind(request_id=request_id)
        status_code = 500
        response_started = False
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Unhandled errors are rendered here (not by Starlette's outer ServerErrorMiddleware)
            # so the response still carries the request ID and the error envelope.
            logger.error("unhandled error", exc_info=exc)
            if response_started:
                raise
            response = _json_error(500, ErrorCode.INTERNAL_ERROR, "Internal error")
            await response(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - started
            route = _route_template(scope)
            method = scope.get("method", "-")
            HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
            HTTP_LATENCY.labels(method, route).observe(duration)
            logger.info(
                "request",
                extra={
                    "operation": f"{method} {route}",
                    "method": method,
                    "path": scope.get("path"),
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            context.clear()


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            try:
                return str(value.decode("latin-1"))
            except UnicodeDecodeError:  # pragma: no cover - latin-1 decodes any bytes
                return None
    return None


def _json_error(
    status: int, code: ErrorCode, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=error_body(code, message, context.request_id(), details)
    )


async def _platform_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PlatformError)
    if exc.http_status >= 500:
        logger.error("platform error", extra={"error_code": str(exc.code)}, exc_info=exc)
    return _json_error(exc.http_status, exc.code, exc.message, exc.details)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only location, message and type: never echo the submitted input (it may hold PII).
    errors = [
        {"loc": list(err.get("loc", ())), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    if any(e["type"] == "json_invalid" for e in errors):
        return _json_error(400, ErrorCode.MALFORMED_REQUEST, "Request body is not valid JSON")
    return _json_error(422, ErrorCode.VALIDATION_ERROR, "Request validation failed", {"errors": errors})


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    mapping = {
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        400: ErrorCode.MALFORMED_REQUEST,
        401: ErrorCode.AUTH_REQUIRED,
        403: ErrorCode.PERMISSION_DENIED,
        429: ErrorCode.RATE_LIMITED,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }
    code = mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    status = exc.status_code if exc.status_code in mapping else 500
    return _json_error(status, code, code.replace("_", " ").capitalize())


def install_error_handlers(app: FastAPI) -> None:
    """Unhandled exceptions are rendered by RequestContextMiddleware."""
    app.add_exception_handler(PlatformError, _platform_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
