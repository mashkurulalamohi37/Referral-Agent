"""Migrations, roles and the insert-only trigger (I2) against a real PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command
from app.core.config import Settings, get_settings
from app.core.db import create_engine
from app.core.migration_helpers import INSERT_ONLY_TABLES, insert_only_sql
from app.core.resources import migration_heads
from app.main import create_app
from tests.integration.conftest import APP_URL, alembic_config

PROBE = "io_probe"


@pytest.fixture
async def insert_only_probe(owner_engine: AsyncEngine) -> AsyncIterator[str]:
    async with owner_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {PROBE}"))
        await conn.execute(text(f"CREATE TABLE {PROBE} (id int PRIMARY KEY, v text)"))
        for stmt in insert_only_sql(PROBE):
            await conn.execute(text(stmt))
    yield PROBE
    async with owner_engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {PROBE}"))


async def test_migrations_at_head(owner_engine: AsyncEngine) -> None:
    async with owner_engine.connect() as conn:
        current = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalars()
        assert frozenset(current) == migration_heads()
        ext = await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'"))
        assert ext.scalar_one() == 1


def test_downgrade_and_upgrade_round_trip(migrated_database: None) -> None:
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")


async def test_insert_only_trigger_blocks_update_delete_truncate(
    insert_only_probe: str, app_engine: AsyncEngine
) -> None:
    async with app_engine.begin() as conn:
        await conn.execute(text(f"INSERT INTO {insert_only_probe} VALUES (1, 'a')"))

    for statement in (
        f"UPDATE {insert_only_probe} SET v = 'b'",
        f"DELETE FROM {insert_only_probe}",
        f"TRUNCATE {insert_only_probe}",
    ):
        with pytest.raises(DBAPIError, match="insert-only"):
            async with app_engine.begin() as conn:
                await conn.execute(text(statement))

    async with app_engine.connect() as conn:
        assert (await conn.execute(text(f"SELECT v FROM {insert_only_probe}"))).scalar_one() == "a"


async def test_app_role_cannot_disable_triggers_or_alter_schema(
    insert_only_probe: str, app_engine: AsyncEngine
) -> None:
    for statement in (
        f"ALTER TABLE {insert_only_probe} DISABLE TRIGGER ALL",
        f"DROP TRIGGER trg_insert_only_{insert_only_probe} ON {insert_only_probe}",
        "SET session_replication_role = replica",
        "CREATE TABLE app_should_not_create (id int)",
    ):
        with pytest.raises((ProgrammingError, DBAPIError)):
            async with app_engine.begin() as conn:
                await conn.execute(text(statement))


async def test_existing_insert_only_tables_have_triggers(owner_engine: AsyncEngine) -> None:
    async with owner_engine.connect() as conn:
        tables = set(
            (await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))).scalars()
        )
        triggers = set(
            (await conn.execute(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"))).scalars()
        )
    for table in INSERT_ONLY_TABLES:
        if table in tables:
            assert f"trg_insert_only_{table}" in triggers
            assert f"trg_insert_only_{table}_truncate" in triggers


def test_ready_endpoint_against_real_infrastructure(migrated_database: None) -> None:
    assert APP_URL
    settings = Settings(
        **{
            **get_settings().model_dump(),
            "database_url": APP_URL,
            "redis_url": os.environ.get("TEST_REDIS_URL", str(get_settings().redis_url)),
        }
    )
    with TestClient(create_app(settings)) as client:
        resp = client.get("/v1/ready")
    assert resp.json() == {"database": "ok", "redis": "ok", "migrations": "ok"}
    assert resp.status_code == 200


async def test_app_engine_sessions_run_in_utc(migrated_database: None) -> None:
    engine = create_engine(get_settings(), url=APP_URL)
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SHOW timezone"))).scalar_one() == "UTC"
    finally:
        await engine.dispose()


def test_worker_runtime_runs_async_unit_of_work(migrated_database: None) -> None:
    """ADR 0002: the per-process loop + engine execute a session-scoped coroutine."""
    from app.worker import runtime, tasks  # noqa: PLC0415

    def in_worker_thread() -> tuple[str, str]:
        # Own thread, like a prefork child: the runtime installs its own event loop there and
        # must not disturb the test runner's loop.
        try:
            first = runtime.run_async(tasks._database_time)
            second = runtime.run_async(tasks._database_time)  # same loop, pooled engine reused
            return first, second
        finally:
            runtime.shutdown_process()

    with ThreadPoolExecutor(max_workers=1) as pool:
        first, second = pool.submit(in_worker_thread).result(timeout=30)
    assert first <= second
