# PulsePOS Integration Guide

Integration guide for the PulsePOS retail and point-of-sale platform.

---

## 1. Scope of Integration

- **Attribution Model**: First-touch with 30-day cookie window.
- **Credit Acceptance**: Cross-product credit enabled (`accepts_cross_product_credit = true`).
- **Commission Defaults**: 10% on initial payment, 5% on monthly renewals for up to 12 months.
- **Visibility**: `MASKED` (Referrer sees "K****m · PulsePOS Standard").

---

## 2. Event Workflow

1. **Merchant Signup**: PulsePOS captures referral code at checkout / signup and calls `client.attribute()`.
2. **Subscription Start**: Emit `subscription.created`.
3. **POS Hardware & Subscription Billing**:
   - `payment.succeeded` with `billing_reason="initial"`.
   - `credit_applied_amount` if merchant redeemed referral credits.
4. **Monthly Subscription Renewal**:
   - `payment.succeeded` with `billing_reason="renewal"`.

```python
from referral_client import PaymentSucceeded, ReferralClient

client = ReferralClient(
    base_url="https://ref.example.com",
    key_id="pulsepos_key",
    secret="pulsepos_secret",
    signing_secret="pulsepos_sig_secret",
)

# Send payment succeeded
await client.send_event(
    PaymentSucceeded(
        payment_id=invoice.id,
        subscription_id=sub.id,
        external_user_id=merchant.id,
        plan_code="pulsepos_pro",
        billing_reason="initial",
        amount_gross=350000,  # ৳3,500 in poisha
        amount_net_paid=350000,
    )
)
```
