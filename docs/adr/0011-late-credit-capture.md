# 0011. Credit capture after reservation expiry or amount mismatch

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 7

## Context

Reservations expire after 15 minutes (§11). `payment.succeeded` is processed
asynchronously (lag target p95 < 30 s) and can be parked for up to 72 h
(`WAITING_DEPENDENCY`). If the expiry job releases a reservation before the payment event
that used it is processed, the customer has already been charged the discounted price
and the referrer also gets the credit back. The credit is spent twice, against I5.
Also undefined: what happens when `credit_applied_amount` differs from `reserved_amount`.

## Decision

### Make the race rare

- The SDK's recommended flow calls `POST /v1/credits/reservations/{id}/capture`
  **synchronously** right after the product's charge succeeds, with
  `{applied_amount, payment_id}`. `payment.succeeded` with `credit_reservation_id` then
  finds the reservation already `CAPTURED` (idempotent no-op).
- Expiry job releases a reservation only after `expires_at + release_grace`
  (default 10 min). Capture is accepted during that grace period.

### Late capture (after release)

If a capture (API or event) references a reservation already `RELEASED`/`EXPIRED`:

- The discount already happened, so the platform records it: posting **P9** draws from
  `credit_only` (up to its positive balance), then `available`, which may go negative
  (§10.4). Reservation state becomes `LATE_CAPTURED`.
- An alert is raised and the case is visible in the admin reservations view.
- **I5 is scoped accordingly**: reservations, on-time captures and payouts never consume
  more than was available. A late capture records a debt for a discount the product
  already gave; it is never an operation the platform can refuse.

### Amount mismatch

- `applied < reserved`: capture `applied`, release the rest (P7 + P8) in one transaction.
- `applied > reserved`: capture `reserved` (P7), and the excess is a late capture (P9) +
  alert. The product should never do this; the per-invoice cap is enforced at reserve
  time, not at capture.
- `applied == 0` on a payment with a reservation ID: release.

## Consequences

- No discount given by a product is ever lost from the ledger.
- Negative balances can result from product misbehaviour; alerts make it visible, and
  per-product counts of late captures go into the product health report.
