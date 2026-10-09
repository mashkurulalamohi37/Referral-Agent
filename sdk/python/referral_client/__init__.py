"""Official Python SDK for Referral & Commission Platform."""

from referral_client.client import ReferralClient
from referral_client.events import (
    BaseEvent,
    PaymentChargeback,
    PaymentRefunded,
    PaymentSucceeded,
    SubscriptionCancelled,
    SubscriptionCreated,
    SubscriptionUpdated,
    UserRegistered,
)
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
from referral_client.webhook import compute_signature, verify_signature

__all__ = [
    "ReferralClient",
    "BaseEvent",
    "UserRegistered",
    "SubscriptionCreated",
    "SubscriptionUpdated",
    "SubscriptionCancelled",
    "PaymentSucceeded",
    "PaymentRefunded",
    "PaymentChargeback",
    "Signals",
    "AttributionRequest",
    "AttributionResponse",
    "CreditBalanceResponse",
    "CreditReservationRequest",
    "CreditReservationResponse",
    "ReferralSDKError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "compute_signature",
    "verify_signature",
]
