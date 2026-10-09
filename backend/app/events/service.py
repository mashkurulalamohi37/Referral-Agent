"""Events public service interface: intake, signatures, outbox, idempotency (§8, docs/erd.md)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import referencing
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.core import clock
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.core.ids import uuid7
from app.events.models import InboundEvent, OutboxMessage
from app.subscriptions import service as subscription_service

# Load compiled event schemas
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "docs" / "events"

_REGISTRY: Registry | None = None
_SCHEMAS: dict[str, dict[str, Any]] = {}
_VALIDATORS: dict[str, Draft202012Validator] = {}


def _init_registry() -> tuple[Registry, dict[str, dict[str, Any]]]:
    global _REGISTRY, _SCHEMAS
    if _REGISTRY is None:
        schemas: dict[str, dict[str, Any]] = {}
        for path in SCHEMA_DIR.rglob("*.schema.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            if "$id" in schema:
                schemas[schema["$id"]] = schema
        _REGISTRY = Registry().with_resources(
            (sid, Resource.from_contents(s)) for sid, s in schemas.items()
        )
        _SCHEMAS = schemas
    return _REGISTRY, _SCHEMAS


def _get_validator(event_type: str) -> Draft202012Validator:
    """Loads and caches Draft202012Validator for an event type."""
    if event_type not in _VALIDATORS:
        registry, _ = _init_registry()
        schema_file = SCHEMA_DIR / f"{event_type}.schema.json"
        if not schema_file.exists():
            raise PlatformError(
                ErrorCode.EVENT_TYPE_UNSUPPORTED,
                f"Unsupported event type: '{event_type}'",
            )
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        _VALIDATORS[event_type] = Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
    return _VALIDATORS[event_type]


def validate_event_data(event_type: str, data: dict[str, Any]) -> None:
    """Validates event data payload against official JSON Schema."""
    validator = _get_validator(event_type)
    errors = list(validator.iter_errors(data))
    if errors:
        first_err = errors[0]
        raise PlatformError(
            ErrorCode.VALIDATION_ERROR,
            f"Event data validation failed for {event_type}: {first_err.message}",
            details={"path": list(first_err.path), "schema_path": list(first_err.schema_path)},
        )


# ---------------------------------------------------------------- Signature Verification (§8.1)


def compute_signature(secret: str, timestamp: int, raw_body: bytes) -> str:
    """Computes hex HMAC-SHA256 signature for payload."""
    payload_to_sign = f"{timestamp}.".encode("utf-8") + raw_body
    sig_hex = hmac.new(secret.encode("utf-8"), payload_to_sign, hashlib.sha256).hexdigest()
    return f"v1={sig_hex}"


def verify_signature(
    *,
    secret: str,
    timestamp_header: str | None,
    signature_header: str | None,
    raw_body: bytes,
    max_drift_seconds: int = 300,
) -> None:
    """Verifies X-Signature and timestamp drift (§8.1)."""
    if not timestamp_header or not signature_header:
        raise PlatformError(ErrorCode.SIGNATURE_INVALID, "Missing signature headers")

    try:
        ts = int(timestamp_header.strip())
    except ValueError as exc:
        raise PlatformError(ErrorCode.SIGNATURE_INVALID, "Invalid timestamp header") from exc

    current_epoch = int(clock.now().timestamp())
    if abs(current_epoch - ts) > max_drift_seconds:
        raise PlatformError(
            ErrorCode.SIGNATURE_TIMESTAMP_STALE,
            f"Timestamp drift of {abs(current_epoch - ts)}s exceeds maximum allowed {max_drift_seconds}s",
        )

    expected = compute_signature(secret, ts, raw_body)
    if not hmac.compare_digest(expected, signature_header.strip()):
        raise PlatformError(ErrorCode.SIGNATURE_INVALID, "HMAC signature mismatch")


# ---------------------------------------------------------------- Inbound Intake & Outbox


async def get_inbound_event(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    event_id: str,
) -> InboundEvent | None:
    """Look up an inbound event by product and event_id."""
    stmt = select(InboundEvent).where(
        InboundEvent.product_id == product_id,
        InboundEvent.event_id == event_id,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def ingest_event(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    raw_body: bytes,
    payload_dict: dict[str, Any],
    timestamp_header: str | None = None,
    signature_header: str | None = None,
    verify_sig: bool = True,
    settings: Settings | None = None,
) -> tuple[InboundEvent, bool]:
    """Ingests an inbound product event, validates signature and idempotency (§8).

    Returns (InboundEvent, is_new_event).
    """
    event_id = payload_dict.get("event_id")
    event_type = payload_dict.get("event_type")
    schema_version = payload_dict.get("schema_version", 1)
    occurred_at_str = payload_dict.get("occurred_at")
    data = payload_dict.get("data", {})

    if not event_id or not event_type or not occurred_at_str:
        raise PlatformError(ErrorCode.MALFORMED_REQUEST, "Event envelope missing required fields")

    # Parse occurred_at
    try:
        occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlatformError(ErrorCode.VALIDATION_ERROR, "Invalid occurred_at timestamp format") from exc

    # 1. Verify signature if required
    if verify_sig:
        product = await catalog_service.get_product_by_id(session, product_id)
        if not product or not product.webhook_signing_secret_enc:
            raise PlatformError(ErrorCode.NOT_FOUND, "Product webhook secret not configured")
        from app.core.security import decrypt_text
        app_settings = settings or get_settings()
        secret = decrypt_text(product.webhook_signing_secret_enc, app_settings.secret_key)
        verify_signature(
            secret=secret,
            timestamp_header=timestamp_header,
            signature_header=signature_header,
            raw_body=raw_body,
        )

    # 2. Validate JSON schema for event data
    validate_event_data(event_type, data)

    # 3. Canonical payload hash
    payload_sha = hashlib.sha256(raw_body).digest()

    # 4. Idempotency on (product_id, event_id)
    existing = await get_inbound_event(session, product_id=product_id, event_id=event_id)
    if existing:
        if existing.payload_sha256 != payload_sha:
            raise PlatformError(
                ErrorCode.EVENT_ID_CONFLICT,
                f"Event ID '{event_id}' reused with conflicting payload",
            )
        return existing, False

    # 5. Check business key conflicts
    if event_type == "payment.succeeded":
        payment_id = data.get("payment_id")
        if payment_id:
            existing_payment = await subscription_service.get_payment_fact(
                session, product_id=product_id, payment_id=payment_id
            )
            if existing_payment:
                raise PlatformError(
                    ErrorCode.BUSINESS_KEY_CONFLICT,
                    f"Payment ID '{payment_id}' was already recorded in a prior event",
                )

    # 6. Insert InboundEvent
    inbound = InboundEvent(
        product_id=product_id,
        event_id=event_id,
        event_type=event_type,
        schema_version=schema_version,
        occurred_at=occurred_at,
        payload_sha256=payload_sha,
        raw_payload=payload_dict,
        status="PENDING",
    )
    session.add(inbound)
    await session.flush()

    # 7. Write to Transactional Outbox (ADR 0006)
    outbox_msg = OutboxMessage(
        aggregate_type="INBOUND_EVENT",
        aggregate_id=inbound.id,
        event_type=event_type,
        payload={
            "inbound_event_id": str(inbound.id),
            "product_id": str(product_id),
            "event_type": event_type,
            "data": data,
        },
        status="PENDING",
        scheduled_at=clock.now(),
    )
    session.add(outbox_msg)
    await session.flush()

    # 8. Process derived facts immediately / synchronously in monolith
    if event_type.startswith("subscription."):
        await subscription_service.process_subscription_event(
            session, product_id=product_id, event_type=event_type, data=data
        )
    elif event_type == "payment.succeeded":
        await subscription_service.record_payment_fact(
            session, product_id=product_id, data=data
        )
    elif event_type == "payment.refunded":
        await subscription_service.record_refund_fact(
            session, product_id=product_id, data=data
        )

    inbound.status = "PROCESSED"
    inbound.processed_at = clock.now()
    await session.flush()

    return inbound, True


async def record_outbox_message(
    session: AsyncSession,
    *,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    status: str = "PENDING",
) -> OutboxMessage:
    """Records an outbox message in the transactional outbox table (§2, ADR 0006)."""
    outbox_msg = OutboxMessage(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        status=status,
        scheduled_at=clock.now(),
    )
    session.add(outbox_msg)
    await session.flush()
    return outbox_msg

