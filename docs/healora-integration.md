# Healora Integration Guide (Healthcare Privacy Protected)

Integration guide for Healora (telemedicine and clinic management platform) with strict health data and privacy isolation (§15, ADR 0016).

---

## 1. Privacy & Healthcare Constraints (MANDATORY)

- **Zero Health Data**: Never send diagnosis codes, prescription details, doctor notes, or medical history. `extra="forbid"` on all schemas strictly rejects unexpected payload fields.
- **Referrer Visibility**: Set to `NONE` (counts only) or `MASKED` (e.g., "K****m · Healora"). The referrer must **never** see clinical information about referred users.
- **Hashed Risk Signals**: Phone numbers and emails are immediately salted and HMAC-hashed on receipt; plaintext signals are never stored in platform tables or logs.

---

## 2. Telemedicine & Clinic Subscription Flow

```python
from referral_client import PaymentSucceeded, ReferralClient, Signals

client = ReferralClient(
    base_url="https://ref.example.com",
    key_id="healora_key",
    secret="healora_secret",
    signing_secret="healora_sig_secret",
)

# 1. Attributed registration (Fail-soft)
await client.attribute(
    external_user_id=doctor.id,
    registered_at=doctor.created_at,
    referral_code=signup_form.referral_code,
    attribution_token=signup_form.rt,
    signals=Signals(
        ip=request.client.host,
        email=doctor.email,
    ),
    fail_soft=True,
)

# 2. Monthly Provider Subscription Event
await client.send_event(
    PaymentSucceeded(
        payment_id=payment.id,
        subscription_id=sub.id,
        external_user_id=doctor.id,
        plan_code="clinic_plus",
        billing_reason="initial",
        amount_gross=200000,  # ৳2,000 in poisha
        amount_net_paid=200000,
    )
)
```
