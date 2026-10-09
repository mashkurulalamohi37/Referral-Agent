"""Exceptions for Referral & Commission SDK."""

from __future__ import annotations

from typing import Any


class ReferralSDKError(Exception):
    """Base exception for all Referral SDK errors."""

    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class AuthenticationError(ReferralSDKError):
    """Raised when API client key or signature is invalid (401)."""


class PermissionDeniedError(ReferralSDKError):
    """Raised when API client lacks required scopes (403)."""


class NotFoundError(ReferralSDKError):
    """Raised when a requested resource is not found (404)."""


class ConflictError(ReferralSDKError):
    """Raised on idempotency conflict or duplicate key (409)."""


class ValidationError(ReferralSDKError):
    """Raised on invalid request body or parameters (422)."""


class RateLimitError(ReferralSDKError):
    """Raised when rate limit is exceeded (429)."""


class ServerError(ReferralSDKError):
    """Raised on internal platform errors (5xx)."""
