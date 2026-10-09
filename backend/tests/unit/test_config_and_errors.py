from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import AppEnv, Settings
from app.core.errors import HTTP_STATUS, ErrorCode, PlatformError, error_body

API_DOC = Path(__file__).resolve().parents[3] / "docs" / "api.md"

_STRONG = "x" * 40


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "database_url": "postgresql+asyncpg://u:p@db:5432/referral",
        "redis_url": "redis://redis:6379/0",
        "jwt_signing_key": _STRONG,
        "attribution_token_key": _STRONG,
        "signal_hash_pepper": _STRONG,
        "payout_details_encryption_key": _STRONG,
        "secrets_encryption_key": _STRONG,
        "referral_base_url": "https://ref.example.com",
        "portal_url": "https://portal.example.com/",
        "admin_url": "https://admin.example.com",
    }
    base.update(overrides)
    return Settings(**base)


class TestSettings:
    def test_prod_accepts_strong_secrets(self) -> None:
        settings = _settings(app_env="prod")
        assert settings.is_production
        assert not settings.docs_enabled
        assert settings.cors_origins == ["https://portal.example.com", "https://admin.example.com"]

    @pytest.mark.parametrize("value", ["dev-only-" + "x" * 40, "short"])
    def test_prod_rejects_dev_or_short_secrets(self, value: str) -> None:
        with pytest.raises(ValidationError, match="SIGNAL_HASH_PEPPER"):
            _settings(app_env="staging", signal_hash_pepper=value)

    def test_local_allows_dev_secrets_and_docs(self) -> None:
        settings = _settings(app_env="local", jwt_signing_key="dev-only")
        assert settings.app_env is AppEnv.LOCAL
        assert settings.docs_enabled

    def test_docs_override(self) -> None:
        assert _settings(app_env="prod", api_docs_enabled=True).docs_enabled

    def test_currencies_from_env_string(self) -> None:
        assert _settings(enabled_currencies="bdt, usd").enabled_currencies == ("BDT", "USD")

    def test_secrets_not_in_repr(self) -> None:
        assert _STRONG not in repr(_settings())


class TestErrors:
    def test_every_code_has_a_status(self) -> None:
        assert set(HTTP_STATUS) == set(ErrorCode)

    @pytest.mark.skipif(not API_DOC.exists(), reason="docs/ not available (container without repo)")
    def test_registry_matches_docs(self) -> None:
        documented: dict[str, int] = {}
        for code, status in re.findall(r"^\| `([A-Z][A-Z0-9_]+)` \| (\d{3}) \|", API_DOC.read_text(encoding="utf-8"), re.M):
            documented[code] = int(status)
        in_code = {str(code): status for code, status in HTTP_STATUS.items()}
        assert in_code == documented

    def test_platform_error(self) -> None:
        err = PlatformError(ErrorCode.SELF_REFERRAL, details={"reason": "same_user"})
        assert err.http_status == 422
        assert err.message == "Self referral"
        assert "SELF_REFERRAL" in str(err)

    def test_error_body_shape(self) -> None:
        body = error_body(ErrorCode.NOT_FOUND, "Not found", "req-1")
        assert body == {
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "Not found", "request_id": "req-1", "details": {}},
        }
