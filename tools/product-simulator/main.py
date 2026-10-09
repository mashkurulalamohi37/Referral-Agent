"""Product Simulator (§19.3).

FastAPI application acting as a connected product (PulsePOS/Healora) to demonstrate
and test end-to-end referral attribution, credit spending, event intake, and refunds.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

# Add sdk/python to path for simulator runtime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sdk/python")))

from referral_client import (
    PaymentChargeback,
    PaymentRefunded,
    PaymentSucceeded,
    ReferralClient,
    Signals,
    SubscriptionCreated,
    UserRegistered,
)

app = FastAPI(
    title="Product Simulator",
    description="Simulates a SaaS tenant (e.g. PulsePOS or Healora) connected to the Referral Platform",
    version="1.0.0",
)

PLATFORM_URL = os.getenv("PLATFORM_URL", "http://localhost:8000")
KEY_ID = os.getenv("PRODUCT_KEY_ID", "key_pulsepos_test")
SECRET = os.getenv("PRODUCT_SECRET", "sec_pulsepos_test")
SIGNING_SECRET = os.getenv("PRODUCT_SIGNING_SECRET", "sig_pulsepos_test")

client = ReferralClient(
    base_url=PLATFORM_URL,
    key_id=KEY_ID,
    secret=SECRET,
    signing_secret=SIGNING_SECRET,
)


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    referral_code: str | None = None
    attribution_token: str | None = None
    ip_address: str | None = "192.168.1.50"


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_user_id: str
    plan_code: str = "standard_monthly"
    gross_amount: int = 200000  # ৳2,000 in poisha
    discount_amount: int = 0
    tax_amount: int = 0
    use_referral_credit: bool = True
    billing_reason: str = "initial"


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    amount_refunded: int
    reservation_id: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "product-simulator"}


@app.post("/simulator/signup")
async def simulate_signup(req: SignupRequest) -> dict[str, Any]:
    """Simulates customer signup, registering user and attributing referral."""
    external_user_id = f"user_{uuid.uuid4().hex[:10]}"
    registered_at = datetime.now(timezone.utc).isoformat()

    attribution = await client.attribute(
        external_user_id=external_user_id,
        registered_at=registered_at,
        referral_code=req.referral_code,
        attribution_token=req.attribution_token,
        signals=Signals(email=req.email, ip=req.ip_address),
        fail_soft=True,
    )

    # Emit user.registered event
    event = UserRegistered(
        external_user_id=external_user_id,
        registered_at=registered_at,
        signals={"email": req.email, "ip": req.ip_address},
    )
    await client.send_event(event)

    return {
        "external_user_id": external_user_id,
        "email": req.email,
        "attributed": attribution is not None and attribution.status == "ATTRIBUTED",
        "attribution": attribution.model_dump() if attribution else None,
    }


@app.post("/simulator/checkout")
async def simulate_checkout(req: CheckoutRequest) -> dict[str, Any]:
    """Simulates checkout: balance check, credit reservation, charge, and payment.succeeded."""
    credit_applied = 0
    reservation_id = None

    if req.use_referral_credit:
        try:
            bal = await client.get_credit_balance(external_user_id=req.external_user_id)
            if bal.spendable_minor > 0:
                needed = req.gross_amount - req.discount_amount
                to_reserve = min(bal.spendable_minor, needed)
                if to_reserve > 0:
                    order_ref = f"ord_{uuid.uuid4().hex[:8]}"
                    resv = await client.reserve_credit(
                        external_user_id=req.external_user_id,
                        requested_amount=to_reserve,
                        order_ref=order_ref,
                    )
                    reservation_id = resv.reservation_id
                    credit_applied = resv.reserved_amount
        except Exception:
            pass  # Fail soft on credit lookup

    net_paid = req.gross_amount - req.discount_amount - req.tax_amount - credit_applied
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    subscription_id = f"sub_{uuid.uuid4().hex[:8]}"

    # Emit subscription.created
    await client.send_event(
        SubscriptionCreated(
            subscription_id=subscription_id,
            external_user_id=req.external_user_id,
            plan_code=req.plan_code,
        )
    )

    # Emit payment.succeeded
    pay_event = PaymentSucceeded(
        payment_id=payment_id,
        subscription_id=subscription_id,
        external_user_id=req.external_user_id,
        plan_code=req.plan_code,
        billing_reason=req.billing_reason,
        amount_gross=req.gross_amount,
        discount_amount=req.discount_amount,
        tax_amount=req.tax_amount,
        credit_applied_amount=credit_applied,
        credit_reservation_id=reservation_id,
        amount_net_paid=net_paid,
    )
    send_res = await client.send_event(pay_event)

    return {
        "payment_id": payment_id,
        "subscription_id": subscription_id,
        "amount_gross": req.gross_amount,
        "credit_applied": credit_applied,
        "amount_net_paid": net_paid,
        "credit_reservation_id": reservation_id,
        "event_receipt": send_res,
    }


@app.post("/simulator/refund")
async def simulate_refund(req: RefundRequest) -> dict[str, Any]:
    """Simulates payment refund and optional credit refund."""
    refund_id = f"ref_{uuid.uuid4().hex[:10]}"
    refund_event = PaymentRefunded(
        refund_id=refund_id,
        payment_id=req.payment_id,
        amount_refunded=req.amount_refunded,
    )
    event_res = await client.send_event(refund_event)

    credit_res = None
    if req.reservation_id:
        try:
            credit_res = await client.refund_credit(
                reservation_id=req.reservation_id,
                amount_minor=req.amount_refunded,
            )
        except Exception as exc:
            credit_res = {"error": str(exc)}

    return {
        "refund_id": refund_id,
        "payment_id": req.payment_id,
        "amount_refunded": req.amount_refunded,
        "event_receipt": event_res,
        "credit_refund": credit_res,
    }


@app.post("/simulator/chargeback")
async def simulate_chargeback(payment_id: str, amount: int) -> dict[str, Any]:
    """Simulates a chargeback dispute on a payment."""
    cb_event = PaymentChargeback(payment_id=payment_id, amount=amount)
    event_res = await client.send_event(cb_event)
    return {"payment_id": payment_id, "amount": amount, "event_receipt": event_res}
