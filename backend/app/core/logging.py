"""Structured JSON logging with mandatory redaction (§15, §22.2).

Logs must never contain passwords, tokens, secrets, raw risk signals (email, phone, IP,
device, payment fingerprint), payout details or health data. Two layers enforce this:

1. Field redaction: any `extra` key (recursively, in dicts and lists) whose name matches a
   sensitive name is replaced with "[REDACTED]".
2. Pattern redaction: the rendered message and string values are scrubbed of bearer
   credentials, JWT/JWS strings, emails, phone numbers, IP addresses and long digit runs.

Callers should still avoid passing sensitive data; this is the safety net, and it is tested.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import traceback
from datetime import UTC, datetime
from typing import Any, Final

from app.core.context import get_log_context

REDACTED: Final = "[REDACTED]"

# Key names are matched two ways: short words only as a whole `_`/`-`/`.` separated segment
# (so "ip" matches "client_ip" but not "relationship"), longer words anywhere in the key.
_SENSITIVE_SEGMENTS: Final = frozenset(
    {
        "ip", "pin", "otp", "totp", "cvv", "card", "email", "phone", "msisdn", "iban",
        "routing", "signal", "signals", "device", "dob", "nid",
    }
)  # fmt: skip
_SENSITIVE_SUBSTRINGS: Final = (
    "password", "passwd", "secret", "token", "authorization", "authorisation", "cookie",
    "signature", "apikey", "api_key", "private_key", "fingerprint", "account_number",
    "account_no", "payout_details", "details_enc", "diagnos", "medical", "clinical",
    "prescription", "health_data", "health_record",
)  # fmt: skip
_KEY_SPLIT = re.compile(r"[_\-.\s]+")


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if any(part in _SENSITIVE_SEGMENTS for part in _KEY_SPLIT.split(lowered)):
        return True
    return any(word in lowered for word in _SENSITIVE_SUBSTRINGS)

_PATTERNS: Final[list[tuple[re.Pattern[str], str]]] = [
    # Authorization: Bearer <anything>
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=:-]+"), r"\1 " + REDACTED),
    # JWT / JWS compact serialisation
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"), REDACTED),
    # key=value or key: value for sensitive keys inside free text
    (
        re.compile(
            r"(?i)\b(password|passwd|secret|token|api_key|signature|otp|pin)\b(\s*[=:]\s*)"
            r"(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
        ),
        r"\1\2" + REDACTED,
    ),
    # email addresses
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), REDACTED),
    # IPv4
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), REDACTED),
    # IPv6 (loose: at least three groups with colons)
    (re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){3,7}[0-9A-Fa-f]{0,4}\b"), REDACTED),
    # phone numbers: E.164 (+8801...), Bangladeshi local (01XXXXXXXXX) and 880-prefixed
    (re.compile(r"\+\d{8,15}\b"), REDACTED),
    (re.compile(r"\b(?:880)?01[3-9]\d{8}\b"), REDACTED),
    # long digit runs (account / card numbers)
    (re.compile(r"\b\d{12,}\b"), REDACTED),
]

_RESERVED_RECORD_ATTRS: Final = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)


def scrub_text(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(value: Any, key: str | None = None) -> Any:
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return scrub_text(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    return scrub_text(str(value))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": scrub_text(record.getMessage()),
        }
        payload.update(get_log_context())
        for key, value in vars(record).items():
            if key not in _RESERVED_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            exc_type, exc, tb = record.exc_info
            payload["exc_type"] = exc_type.__name__ if exc_type else None
            payload["exc"] = scrub_text("".join(traceback.format_exception(exc_type, exc, tb)))
        safe = {k: redact(v, k) for k, v in payload.items() if k not in ("msg", "exc")}
        safe["msg"] = payload["msg"]
        if "exc" in payload:
            safe["exc"] = payload["exc"]
        return json.dumps(safe, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log is replaced by our request middleware (no client IPs, §15).
    for name in ("uvicorn", "uvicorn.error", "celery", "alembic"):
        lg = logging.getLogger(name)
        lg.handlers[:] = []
        lg.propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers[:] = []
    access.propagate = False
    access.disabled = True
