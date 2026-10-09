"""Process-wide infrastructure handles (DB engine, session factory, Redis)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import BACKEND_ROOT, Settings
from app.core.db import create_engine, create_session_factory


@dataclass(slots=True)
class Resources:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis: Redis

    @classmethod
    def create(cls, settings: Settings) -> Resources:
        engine = create_engine(settings)
        return cls(
            settings=settings,
            engine=engine,
            session_factory=create_session_factory(engine),
            redis=Redis.from_url(str(settings.redis_url), decode_responses=True),
        )

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()


@lru_cache(maxsize=1)
def migration_heads() -> frozenset[str]:
    """Alembic head revision(s) shipped with this build."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    return frozenset(ScriptDirectory.from_config(config).get_heads())
