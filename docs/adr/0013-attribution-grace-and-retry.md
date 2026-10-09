# 0013. Attribution grace window and durable retry

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 3

## Context

§7.3 accepts an attribution only if `registered_at` is within
`attribution_grace_minutes` (default 60) of the call, and the SDK fails soft so signup
is never blocked. If the platform is unavailable for longer than the grace window, every
signup in that period loses its attribution permanently. The grace window exists to stop
old, existing customers from being attributed, which the "no prior paid events" rule
also guards.

## Decision

- Default `attribution_grace_minutes` = **1440 (24 h)**, configurable per product
  (minimum 15, maximum 4320).
- An attribution is rejected (`ATTRIBUTION_NOT_NEW_ACCOUNT`) if **any** of:
  - `registered_at` older than the grace window at call time;
  - a `payment.succeeded` is already recorded for that product account;
  - the attribution token's `iat` (click time) is after `registered_at` + 5 min
    (click after signup: the token cannot have caused the signup).
- `registered_at` more than 5 min in the future is rejected
  (`ATTRIBUTION_TIMESTAMP_INVALID`).
- The SDKs ship a **durable retry helper**: on failure, the attribution request is
  written to the product's own outbox table (SQL migration snippet provided for Postgres
  and MySQL) and retried with backoff for up to the grace window. Fail-soft remains the
  default for the synchronous call.

## Consequences

- A platform outage shorter than 24 h loses no attributions if the product uses the
  retry helper.
- Products must send `registered_at` from their own records, not "now" at retry time.
  The integration test checklist covers this.
