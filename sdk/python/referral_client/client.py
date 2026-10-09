"""Referral & Commission Platform Python Client (§19.1)."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any

import httpx

from referral_client.events import BaseEvent
from referral_client.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ReferralSDKError,
    ServerError,
    ValidationError,
)
from referral_client.models import (
    AttributionRequest,
    AttributionResponse,
    CreditBalanceResponse,
    CreditReservationRequest,
    CreditReservationResponse,
    Signals,
)
from referral_client.webhook import compute_signature


class ReferralClient:
    """Async client for interacting with the Referral Platform (§19.1)."""

    def __init__(
        self,
        base_url: str,
        key_id: str,
        secret: str,
        signing_secret: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.key_id = key_id
        self.secret = secret
        self.signing_secret = signing_secret
        self.timeout = timeout
        self.max_retries = max_retries
        self._auth_header = f"Bearer {key_id}.{secret}"

    def _build_signed_headers(self, raw_body: bytes) -> dict[str, str]:
        timestamp = int(time.time())
        signature = compute_signature(self.signing_secret, timestamp, raw_body)
        return {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "X-Signature-Timestamp": str(timestamp),
            "X-Signature": signature,
        }

    def _handle_error_response(self, response: httpx.Response) -> None:
        status = response.status_code
        try:
            body = response.json()
            err_info = body.get("error", {})
            msg = err_info.get("message") or response.text
            code = err_info.get("code")
            details = err_info.get("details")
        except Exception:
            msg = response.text
            code = None
            details = None

        if status == 401:
            raise AuthenticationError(msg, code, details)
        elif status == 403:
            raise PermissionDeniedError(msg, code, details)
        elif status == 404:
            raise NotFoundError(msg, code, details)
        elif status == 409:
            raise ConflictError(msg, code, details)
        elif status == 422:
            raise ValidationError(msg, code, details)
        elif status == 429:
            raise RateLimitError(msg, code, details)
        elif status >= 500:
            raise ServerError(msg, code, details)
        else:
            raise ReferralSDKError(msg, code, details)

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        req_headers = {"Authorization": self._auth_header, "Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(method, url, content=data, headers=req_headers, params=params)
                if resp.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        time.sleep(0.1 * (2 ** attempt))
                        continue
                if resp.is_error:
                    self._handle_error_response(resp)
                return resp
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                raise ServerError(f"Network error communicating with platform: {exc}") from exc

        if last_exc:
            raise ServerError(f"Request failed after {self.max_retries} retries: {last_exc}") from last_exc
        raise ServerError("Unknown request failure")

    async def attribute(
        self,
        *,
        external_user_id: str,
        registered_at: datetime | str,
        referral_code: str | None = None,
        attribution_token: str | None = None,
        signals: Signals | dict[str, Any] | None = None,
        fail_soft: bool = True,
    ) -> AttributionResponse | None:
        """Attributes a new user signup to a referrer (§7, §19.1)."""
        reg_iso = registered_at.isoformat() if isinstance(registered_at, datetime) else str(registered_at)
        signals_dict = signals.model_dump() if isinstance(signals, Signals) else signals

        body = {
            "external_user_id": external_user_id,
            "registered_at": reg_iso,
            "referral_code": referral_code,
            "attribution_token": attribution_token,
            "signals": signals_dict,
        }

        try:
            resp = await self._request_with_retry("POST", "/v1/attributions", data=json.dumps(body).encode("utf-8"))
            data = resp.json()
            return AttributionResponse(**data)
        except Exception as exc:
            if fail_soft:
                return None
            raise

    async def send_event(self, event: BaseEvent | dict[str, Any]) -> dict[str, Any]:
        """Sends a signed event to the platform (§8, §19.1)."""
        payload = event.to_envelope() if isinstance(event, BaseEvent) else event
        raw_body = json.dumps(payload).encode("utf-8")
        headers = self._build_signed_headers(raw_body)
        resp = await self._request_with_retry("POST", "/v1/events", data=raw_body, headers=headers)
        return resp.json()

    async def get_credit_balance(self, *, external_user_id: str, currency: str = "BDT") -> CreditBalanceResponse:
        """Fetches spendable subscription credit balance (§11)."""
        resp = await self._request_with_retry(
            "GET",
            "/v1/credits/balance",
            params={"external_user_id": external_user_id, "currency": currency},
        )
        return CreditBalanceResponse(**resp.json())

    async def reserve_credit(
        self,
        *,
        external_user_id: str,
        requested_amount: int,
        order_ref: str,
        idempotency_key: str | None = None,
        currency: str = "BDT",
    ) -> CreditReservationResponse:
        """Reserves subscription credit for an order (§11)."""
        key = idempotency_key or f"resv_{uuid.uuid4().hex}"
        body = {
            "external_user_id": external_user_id,
            "requested_amount": requested_amount,
            "order_ref": order_ref,
            "idempotency_key": key,
            "currency": currency,
        }
        resp = await self._request_with_retry("POST", "/v1/credits/reservations", data=json.dumps(body).encode("utf-8"))
        return CreditReservationResponse(**resp.json())

    async def capture_credit(
        self,
        *,
        reservation_id: str,
        amount_minor: int | None = None,
        payment_id: str | None = None,
    ) -> dict[str, Any]:
        """Captures a reserved credit (§11)."""
        body = {"amount_minor": amount_minor, "payment_id": payment_id}
        resp = await self._request_with_retry(
            "POST",
            f"/v1/credits/reservations/{reservation_id}/capture",
            data=json.dumps(body).encode("utf-8"),
        )
        return resp.json()

    async def release_credit(self, *, reservation_id: str) -> dict[str, Any]:
        """Releases a reserved credit (§11)."""
        resp = await self._request_with_retry(
            "POST",
            f"/v1/credits/reservations/{reservation_id}/release",
        )
        return resp.json()

    async def refund_credit(
        self,
        *,
        reservation_id: str,
        amount_minor: int,
        idempotency_key: str | None = None,
        currency: str = "BDT",
    ) -> dict[str, Any]:
        """Refunds captured credit (§12)."""
        key = idempotency_key or f"cr_ref_{uuid.uuid4().hex}"
        body = {
            "reservation_id": reservation_id,
            "amount_minor": amount_minor,
            "idempotency_key": key,
            "currency": currency,
        }
        resp = await self._request_with_retry("POST", "/v1/credits/refunds", data=json.dumps(body).encode("utf-8"))
        return resp.json()
