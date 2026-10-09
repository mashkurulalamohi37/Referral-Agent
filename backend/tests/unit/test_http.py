"""Error envelope, request IDs and ops endpoints, without real infrastructure."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.main import create_app


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int


def _test_routes() -> APIRouter:
    router = APIRouter()

    @router.post("/echo")
    async def echo(body: _Body) -> dict[str, int]:
        return {"amount": body.amount}

    @router.get("/platform-error")
    async def platform_error() -> None:
        raise PlatformError(ErrorCode.SELF_REFERRAL, "Self referral is not allowed")

    @router.get("/server-error")
    async def server_error() -> None:
        raise PlatformError(ErrorCode.LEDGER_UNBALANCED)

    @router.get("/crash")
    async def crash() -> None:
        msg = "boom with password=hunter2"
        raise RuntimeError(msg)

    return router


@pytest.fixture
def app() -> FastAPI:
    application = create_app(get_settings())
    application.include_router(_test_routes(), prefix="/test")
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _assert_envelope(resp_json: dict[str, object], code: str) -> None:
    assert resp_json["success"] is False
    error = resp_json["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert error["request_id"] not in ("", "-")


def test_health(client: TestClient) -> None:
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["x-request-id"]


def test_request_id_is_propagated_when_valid(client: TestClient) -> None:
    resp = client.get("/v1/health", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["x-request-id"] == "abc-123"


def test_request_id_is_replaced_when_invalid(client: TestClient) -> None:
    resp = client.get("/v1/health", headers={"X-Request-ID": "bad id with spaces <script>"})
    assert resp.headers["x-request-id"] != "bad id with spaces <script>"
    assert len(resp.headers["x-request-id"]) == 36


def test_not_found_envelope(client: TestClient) -> None:
    resp = client.get("/v1/nope", headers={"X-Request-ID": "req-404"})
    assert resp.status_code == 404
    _assert_envelope(resp.json(), "NOT_FOUND")
    assert resp.json()["error"]["request_id"] == "req-404"


def test_method_not_allowed(client: TestClient) -> None:
    resp = client.delete("/v1/health")
    assert resp.status_code == 405
    _assert_envelope(resp.json(), "METHOD_NOT_ALLOWED")


def test_validation_error_does_not_echo_input(client: TestClient) -> None:
    resp = client.post("/test/echo", json={"amount": "lots", "email": "k@x.com"})
    assert resp.status_code == 422
    body = resp.json()
    _assert_envelope(body, "VALIDATION_ERROR")
    assert "k@x.com" not in resp.text
    locs = [tuple(e["loc"]) for e in body["error"]["details"]["errors"]]
    assert ("body", "amount") in locs
    assert ("body", "email") in locs  # extra="forbid"


def test_malformed_json(client: TestClient) -> None:
    resp = client.post("/test/echo", content=b"{not json", headers={"content-type": "application/json"})
    assert resp.status_code == 400
    _assert_envelope(resp.json(), "MALFORMED_REQUEST")


def test_platform_error_envelope(client: TestClient) -> None:
    resp = client.get("/test/platform-error")
    assert resp.status_code == 422
    _assert_envelope(resp.json(), "SELF_REFERRAL")
    assert resp.json()["error"]["message"] == "Self referral is not allowed"


def test_platform_5xx_error(client: TestClient) -> None:
    resp = client.get("/test/server-error")
    assert resp.status_code == 500
    _assert_envelope(resp.json(), "LEDGER_UNBALANCED")


def test_unhandled_error_hides_details(client: TestClient) -> None:
    resp = client.get("/test/crash", headers={"X-Request-ID": "req-crash"})
    assert resp.status_code == 500
    _assert_envelope(resp.json(), "INTERNAL_ERROR")
    assert resp.headers["x-request-id"] == "req-crash"
    assert "hunter2" not in resp.text
    assert "Traceback" not in resp.text


def test_metrics_exposed(client: TestClient) -> None:
    client.get("/v1/health")
    resp = client.get("/v1/metrics")
    assert resp.status_code == 200
    assert 'http_requests_total{method="GET",route="/health",status="200"}' in resp.text


def test_docs_enabled_in_test_env(client: TestClient) -> None:
    assert client.get("/v1/openapi.json").status_code == 200


def test_ready_fails_closed_when_dependencies_are_down() -> None:
    settings = Settings(
        **{
            **get_settings().model_dump(),
            "database_url": "postgresql+asyncpg://nobody:x@127.0.0.1:1/none",
            "redis_url": "redis://127.0.0.1:1/0",
        }
    )
    with TestClient(create_app(settings)) as client:
        resp = client.get("/v1/ready")
    assert resp.status_code == 503
    assert resp.json() == {"database": "fail", "redis": "fail", "migrations": "unknown"}
