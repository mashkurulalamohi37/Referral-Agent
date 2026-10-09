"""Ops endpoints (§20): /health, /ready, /metrics."""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.resources import Resources, migration_heads

router = APIRouter(tags=["ops"])
logger = logging.getLogger(__name__)

_CHECK_TIMEOUT_S = 2.0


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    database: Literal["ok", "fail"]
    redis: Literal["ok", "fail"]
    migrations: Literal["ok", "behind", "unknown"]


@router.get("/health", response_model=Health)
async def health() -> Health:
    return Health()


async def _check_database(resources: Resources) -> tuple[bool, str]:
    try:
        async with resources.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            rows = (await conn.execute(text("SELECT version_num FROM alembic_version"))).all()
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("readiness: database check failed", extra={"error": type(exc).__name__})
        return False, "unknown"
    current = frozenset(str(r[0]) for r in rows)
    return True, "ok" if current == migration_heads() else "behind"


async def _check_redis(resources: Resources) -> bool:
    try:
        return bool(await resources.redis.ping())
    except (RedisError, OSError) as exc:
        logger.warning("readiness: redis check failed", extra={"error": type(exc).__name__})
        return False


@router.get("/ready", response_model=Readiness, responses={503: {"model": Readiness}})
async def ready(request: Request) -> JSONResponse:
    resources: Resources = request.app.state.resources
    try:
        (db_ok, migrations), redis_ok = await asyncio.wait_for(
            asyncio.gather(_check_database(resources), _check_redis(resources)),
            timeout=_CHECK_TIMEOUT_S,
        )
    except TimeoutError:
        db_ok, migrations, redis_ok = False, "unknown", False
    body = Readiness(
        database="ok" if db_ok else "fail",
        redis="ok" if redis_ok else "fail",
        migrations=migrations,  # type: ignore[arg-type]
    )
    healthy = db_ok and redis_ok and migrations == "ok"
    return JSONResponse(status_code=200 if healthy else 503, content=body.model_dump())


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
