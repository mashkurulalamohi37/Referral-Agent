# 0014. Referral `EXPIRED` uses a conversion window

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 3

## Context

§7.4 says a referral becomes `EXPIRED` with "no conversion within window". The only
window defined is the attribution token window (click → signup). Expiry needs a
signup → first payment window.

## Decision

- New per-product setting `conversion_window_days` (default **90**), overridable per
  campaign.
- A referral in `ATTRIBUTED` or `TRIALING` with no `payment.succeeded` within
  `conversion_window_days` of `attributed_at` becomes `EXPIRED` (daily Beat job,
  idempotent).
- A payment arriving after expiry creates no commission; the payment is recorded and the
  event outcome is `IGNORED` with reason `REFERRAL_EXPIRED`.
- `EXPIRED` releases the I6 slot: the partial unique index on active referrals excludes
  `EXPIRED`, `REJECTED` and `REVOKED`. A new attribution of that account still requires
  admin action, because the account is no longer new (ADR 0013).

## Consequences

- Referrers see stale referrals close out instead of staying "attributed" forever.
