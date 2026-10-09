"""Application settings, loaded from the environment (see .env.example)."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Placeholder secrets shipped in .env.example. Refused outside local/test.
_DEV_SECRET_MARKER = "dev-only"
_MIN_SECRET_LENGTH = 32


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", frozen=True)

    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"

    database_url: PostgresDsn
    migration_database_url: PostgresDsn | None = None
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    redis_url: RedisDsn

    jwt_signing_key: SecretStr
    attribution_token_key: SecretStr
    signal_hash_pepper: SecretStr
    payout_details_encryption_key: SecretStr
    secrets_encryption_key: SecretStr

    referral_base_url: AnyHttpUrl
    portal_url: AnyHttpUrl
    admin_url: AnyHttpUrl

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None

    sentry_dsn: SecretStr | None = None
    otel_exporter_otlp_endpoint: AnyHttpUrl | None = None

    default_time_zone: str = "Asia/Dhaka"
    enabled_currencies: Annotated[tuple[str, ...], NoDecode] = ("BDT",)
    api_docs_enabled: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _split_currencies(cls, data: object) -> object:
        if isinstance(data, dict):
            raw = data.get("enabled_currencies")
            if isinstance(raw, str):
                data["enabled_currencies"] = tuple(
                    c.strip().upper() for c in raw.split(",") if c.strip()
                )
        return data

    @model_validator(mode="after")
    def _check_production_secrets(self) -> Self:
        if self.app_env in (AppEnv.LOCAL, AppEnv.TEST):
            return self
        for name in (
            "jwt_signing_key",
            "attribution_token_key",
            "signal_hash_pepper",
            "payout_details_encryption_key",
            "secrets_encryption_key",
        ):
            value: SecretStr = getattr(self, name)
            secret = value.get_secret_value()
            if _DEV_SECRET_MARKER in secret or len(secret) < _MIN_SECRET_LENGTH:
                msg = f"{name.upper()} must be a real secret of at least {_MIN_SECRET_LENGTH} chars"
                raise ValueError(msg)
        return self

    @property
    def docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.app_env in (AppEnv.LOCAL, AppEnv.TEST)

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnv.PROD

    @property
    def cors_origins(self) -> list[str]:
        return [str(self.portal_url).rstrip("/"), str(self.admin_url).rstrip("/")]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
