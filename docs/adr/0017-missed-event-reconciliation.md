# 0017. Product payment reconciliation to catch missed events

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 13

## Context

If a product never sends `payment.succeeded` (bug, lost outbox, misconfiguration), the
commission silently never exists. Idempotency protects against duplicates, not against
omissions.

## Decision

- New service endpoint `POST /v1/reconciliation/payments` (scope `events:write`).
  The product submits, per day, the list of `(payment_id, external_user_id, amount_net_paid,
  currency, paid_at)` for **referred** accounts (it can query
  `GET /v1/attributions/{external_user_id}` or keep a local flag).
- The platform compares against `payments` and returns, and stores as a
  `reconciliation_run`: missing on platform, amount mismatch, unknown on product.
- Missing payments are **not** auto-created from the reconciliation body (it is not a
  signed event with full fields). An alert asks the product to resend the event.
- The SDK includes a daily job helper. The admin dashboard shows the last run per
  product.
- Delivered in Phase 13 with reports; not required for MVP.

## Consequences

- Silent loss becomes detectable within a day.
