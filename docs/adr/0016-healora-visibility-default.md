# 0016. Healora referrer visibility defaults to `NONE`

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 9

## Context

§15 sets `referrer_visibility` per product with default `MASKED`
("K\*\*\*\*m · Healora"). For a healthcare product, the masked row still tells the
referrer that a person they know (a masked name is easy to guess among one's own
invitees) uses a health service. Q12 leaves Healora's value to legal advice.

## Decision

- Product registry gains a `sensitive_category` flag. For products with the flag set,
  the default visibility is **`NONE`** (counts and amounts only, no per-referral rows).
- Healora is seeded with `sensitive_category = true`.
- `FULL` still requires the per-account consent flag from the product, and on sensitive
  products also requires an admin to enable `FULL` (audited).
- Notifications for sensitive products never name the referred user or the product in
  push/email subject lines ("You earned a commission" rather than
  "Karim joined Healora").

## Consequences

- Healora referrers see "3 referrals, ৳600 earned" without per-person rows until legal
  approves `MASKED`.
