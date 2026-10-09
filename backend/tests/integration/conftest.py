"""Integration tests run against real PostgreSQL and Redis.

Required environment (set by docker-compose.dev.yml for the `api` service, and by CI):
    TEST_DATABASE_URL            app role (DML only) on the test database
    TEST_MIGRATION_DATABASE_URL  owner role on the test database
    TEST_REDIS_URL               optional, defaults to the conftest value
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import command
from alembic.config import Config
from app.core.config import BACKEND_ROOT

OWNER_URL = os.environ.get("TEST_MIGRATION_DATABASE_URL")
APP_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.integration


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if OWNER_URL and APP_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL / TEST_MIGRATION_DATABASE_URL not set")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


def alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.attributes["database_url"] = OWNER_URL
    return config


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Fresh schema at head for the test database (downgrade to base first)."""
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def owner_engine(migrated_database: None) -> AsyncIterator[AsyncEngine]:
    assert OWNER_URL
    engine = create_async_engine(OWNER_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_engine(migrated_database: None) -> AsyncIterator[AsyncEngine]:
    assert APP_URL
    engine = create_async_engine(APP_URL)
    yield engine
    await engine.dispose()
