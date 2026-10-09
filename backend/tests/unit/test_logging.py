"""Log redaction (§15, §22.4 'log redaction')."""

from __future__ import annotations

import json
import logging

import pytest

from app.core import context
from app.core.logging import REDACTED, JsonFormatter, is_sensitive_key, redact, scrub_text


def _render(msg: str, *args: object, exc: BaseException | None = None, **extra: object) -> dict[str, object]:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, msg, args or None, None)
    if exc is not None:
        record.exc_info = (type(exc), exc, exc.__traceback__)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    "key",
    [
        "password", "new_password", "client_secret", "access_token", "refresh_token",
        "Authorization", "cookie", "x_signature", "api_key", "otp", "pin", "email",
        "referrer_email", "phone", "msisdn", "ip", "client_ip", "device_id", "device",
        "payment_fingerprint", "account_number", "card", "payout_details", "details_enc",
        "signals", "diagnosis", "medical_history",
    ],
)  # fmt: skip
def test_sensitive_keys(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize(
    "key",
    ["request_id", "user_id", "product_id", "event_id", "operation", "status", "duration_ms",
     "relationship", "ownership", "shipping", "description", "method", "path"],
)  # fmt: skip
def test_non_sensitive_keys(key: str) -> None:
    assert not is_sensitive_key(key)


@pytest.mark.parametrize(
    ("text", "leaked"),
    [
        ("Authorization: Bearer abcd1234.secretpart", "abcd1234.secretpart"),
        ("token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl here", "eyJhbGciOiJIUzI1NiJ9"),
        ("password=hunter2 next", "hunter2"),
        ('secret: "s3cr3t value"', "s3cr3t value"),
        ("user k@x.com signed up", "k@x.com"),
        ("from 103.4.5.6 today", "103.4.5.6"),
        ("ipv6 2001:db8:85a3:0:0:8a2e:370:7334 seen", "2001:db8:85a3"),
        ("call +8801712345678 now", "+8801712345678"),
        ("call 01712345678 now", "01712345678"),
        ("acct 1234567890123456 paid", "1234567890123456"),
    ],
)
def test_scrub_text_removes_secrets_and_signals(text: str, leaked: str) -> None:
    scrubbed = scrub_text(text)
    assert leaked not in scrubbed
    assert REDACTED in scrubbed


@pytest.mark.parametrize(
    "text",
    [
        "processed payment.succeeded at 2026-10-08 14:58:00",
        "unix ts 1791470400",
        "commission 20000 BDT for HLR-456",
        "request 01929a4e-7c3b-7d2e-9f10-2b3c4d5e6f70",
    ],
)
def test_scrub_text_keeps_ordinary_values(text: str) -> None:
    assert scrub_text(text) == text


def test_redact_nested_structures() -> None:
    value = {
        "user_id": "u1",
        "signals": {"ip": "1.2.3.4"},
        "items": [{"email": "a@b.co", "amount": 5}, "plain", "x@y.org"],
        "nested": {"payout": {"account_number": "017"}},
        "count": 3,
        "flag": True,
        "ratio": 0.5,
        "nothing": None,
        "obj": object(),
    }
    out = redact(value)
    assert out["user_id"] == "u1"
    assert out["signals"] == REDACTED
    assert out["items"][0] == {"email": REDACTED, "amount": 5}
    assert out["items"][2] == REDACTED
    assert out["nested"]["payout"]["account_number"] == REDACTED
    assert out["count"] == 3
    assert out["flag"] is True
    assert isinstance(out["obj"], str)


def test_formatter_emits_json_with_context_and_redacts_extras() -> None:
    context.clear()
    context.bind(request_id="req-1", product_id="healora", user_id=None)
    try:
        out = _render(
            "attributed %s", "k@x.com", email="k@x.com", operation="attribution", status=201
        )
    finally:
        context.clear()
    assert out["msg"] == f"attributed {REDACTED}"
    assert out["request_id"] == "req-1"
    assert out["product_id"] == "healora"
    assert "user_id" not in out
    assert out["email"] == REDACTED
    assert out["operation"] == "attribution"
    assert out["status"] == 201
    assert out["level"] == "INFO"


def test_formatter_scrubs_exception_text() -> None:
    try:
        raise RuntimeError("failed for password=hunter2 and k@x.com")  # noqa: TRY301
    except RuntimeError as exc:
        out = _render("boom", exc=exc)
    assert "hunter2" not in json.dumps(out)
    assert "k@x.com" not in json.dumps(out)
    assert out["exc_type"] == "RuntimeError"


def test_configure_logging_installs_json_handler(capsys: pytest.CaptureFixture[str]) -> None:
    from app.core.logging import configure_logging  # noqa: PLC0415

    configure_logging("INFO")
    logging.getLogger("app.test").info("hello", extra={"token": "abc"})
    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["msg"] == "hello"
    assert payload["token"] == REDACTED
    assert logging.getLogger("uvicorn.access").disabled
