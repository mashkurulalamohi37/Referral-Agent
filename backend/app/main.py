"""ASGI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    catalog,
    commissions,
    credits,
    events,
    identity,
    ledger,
    notifications,
    ops,
    payouts,
    referrals,
    reporting,
    risk,
)
from app.core.config import Settings, get_settings
from app.core.http import RequestContextMiddleware, install_error_handlers
from app.core.logging import configure_logging
from app.core.resources import Resources

API_PREFIX = "/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.resources = Resources.create(settings)
        try:
            yield
        finally:
            await app.state.resources.close()

    docs = settings.docs_enabled
    app = FastAPI(
        title="Referral & Commission Platform",
        version="1.0.0",
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json" if docs else None,
        docs_url=f"{API_PREFIX}/docs" if docs else None,
        redoc_url=f"{API_PREFIX}/redoc" if docs else None,
    )
    app.state.settings = settings

    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    # Added last = outermost: every response, including errors, gets a request ID.
    app.add_middleware(RequestContextMiddleware)

    app.include_router(ops.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(identity.router, prefix=API_PREFIX)
    app.include_router(catalog.router, prefix=API_PREFIX)
    app.include_router(events.router)
    app.include_router(referrals.router)
    app.include_router(commissions.router)
    app.include_router(ledger.router)
    app.include_router(credits.router)
    app.include_router(payouts.router)
    app.include_router(risk.router)
    app.include_router(notifications.router)
    app.include_router(reporting.router)
    return app

