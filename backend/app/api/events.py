"""Inbound Event Ingestion API endpoint (§8, docs/openapi.yaml)."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    authenticate_api_client_dep,
    get_db_session,
    require_api_scopes,
)
from app.catalog.models import ApiClient
from app.core.config import Settings, get_settings
from app.core.errors import ErrorCode, PlatformError
from app.events import service as event_service

router = APIRouter(tags=["events"])


@router.post(
    "/v1/events",
    summary="Inbound event intake (§8.1)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_event_endpoint(
    request: Request,
    response: Response,
    api_client: Annotated[ApiClient, Depends(require_api_scopes("events:write"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_signature_timestamp: Annotated[str | None, Header(alias="X-Signature-Timestamp")] = None,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> dict[str, Any]:
    raw_body = await request.body()
    try:
        payload_dict = json.loads(raw_body)
    except Exception as exc:
        raise PlatformError(ErrorCode.MALFORMED_REQUEST, "Invalid JSON body") from exc

    # Ingest event and enforce idempotency & signature verification
    event_record, is_new = await event_service.ingest_event(
        session,
        product_id=api_client.product_id,
        raw_body=raw_body,
        payload_dict=payload_dict,
        timestamp_header=x_signature_timestamp,
        signature_header=x_signature,
        verify_sig=True,
        settings=settings,
    )

    if not is_new:
        response.status_code = status.HTTP_200_OK
        return {
            "success": True,
            "data": {
                "event_id": event_record.event_id,
                "status": "DUPLICATE",
                "platform_event_id": str(event_record.id),
            },
        }

    return {
        "success": True,
        "data": {
            "event_id": event_record.event_id,
            "status": "ACCEPTED",
            "platform_event_id": str(event_record.id),
        },
    }
