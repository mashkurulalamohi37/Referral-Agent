from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Settings are read from the environment; give unit tests a complete, local-only set before any
# app module calls get_settings(). Integration tests override DATABASE_URL / REDIS_URL.
_TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": os.environ.get(
        "TEST_DATABASE_URL", "postgresql+asyncpg://referral_app:x@localhost:5433/referral_test"
    ),
    "REDIS_URL": os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/15"),
    "JWT_SIGNING_KEY": "dev-only-test-jwt-key-0000000000000000",
    "ATTRIBUTION_TOKEN_KEY": "dev-only-test-attr-key-000000000000000",
    "SIGNAL_HASH_PEPPER": "dev-only-test-pepper-0000000000000000000",
    "PAYOUT_DETAILS_ENCRYPTION_KEY": "dev-only-test-payout-key-00000000000000",
    "SECRETS_ENCRYPTION_KEY": "dev-only-test-secrets-key-0000000000000",
    "REFERRAL_BASE_URL": "http://ref.test",
    "PORTAL_URL": "http://portal.test",
    "ADMIN_URL": "http://admin.test",
}
# Forced, not defaulted: inside the dev container DATABASE_URL points at the real dev database,
# and tests must never touch it.
os.environ.update(_TEST_ENV)


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    from app.core.config import get_settings  # noqa: PLC0415

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
