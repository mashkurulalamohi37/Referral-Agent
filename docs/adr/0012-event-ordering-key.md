# 0012. Event ordering lock is per product account

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 4

## Context

§8.4 processes events for one subscription in order under a per-key advisory lock. But
`payment.refunded`, `payment.chargeback` and `payment.failed` do not carry
`subscription_id`, and `one_time` payments have no subscription.

## Decision

- The ordering key is the **product account**: `(product_id, external_user_id)`.
- Events without `external_user_id` resolve it from the referenced payment
  (`payment_id → payments.product_account_id`). If the payment is unknown, the event is
  parked `WAITING_DEPENDENCY` (§8.4) under the key `(product_id, payment:{payment_id})`
  and re-keyed once the payment arrives.
- Lock: `pg_advisory_xact_lock(hashtextextended(product_id || ':' || external_user_id, 0))`
  held for the processing transaction.
- Within a key, events are processed by `occurred_at`, then `received_at`.

## Consequences

- Slightly coarser serialization (all subscriptions of one account), which is
  harmless at the target load (§22.1) and removes a class of cross-subscription races
  (e.g. an upgrade and a refund on two subscriptions).
