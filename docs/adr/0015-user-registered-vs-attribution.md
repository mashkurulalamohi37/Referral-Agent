# 0015. `user.registered` is informational; attribution only via API

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 3

## Context

§8.3 defines a `user.registered` event, and §7.2 defines `POST /v1/attributions`. The
spec does not say which creates what, or in what order they arrive.

## Decision

- `POST /v1/attributions` is the **only** way to attribute an account. It upserts the
  `product_account`.
- `user.registered` upserts the `product_account` (setting `registered_at` if unknown)
  and records hashed risk signals. It never creates or changes an attribution.
- Either may arrive first. `registered_at` is set by whichever arrives first and is
  never overwritten by a later, different value (a mismatch is logged).
- Products are encouraged, not required, to send `user.registered` for all signups,
  because it improves risk signals (shared device/IP across accounts).

## Consequences

- No hidden attribution path; idempotency rules of §7.3 apply in one place.
