# 0021. Tier counts are evaluated at commission creation

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 5

## Context

§9.3 chooses a `TIERED` rate by the referrer's count of AVAILABLE conversions in the tier
period, evaluated at commission creation. Because confirmation runs every 15 minutes,
two payments a few minutes apart can see different counts depending on when the
confirmation job ran.

## Decision

- Keep the spec's rule: count at creation, not retroactive.
- "Conversion" = a referral whose first commission is AVAILABLE (not reversed to zero)
  and whose `converted_at` falls in the tier period.
- The count, period bounds and chosen tier are stored in `calculation_snapshot` (I8), so
  the result is reproducible even though it depends on timing.
- The rule simulator shows the referrer's current count and which tier applies.

## Consequences

- Referrers may occasionally receive the lower tier for a payment that arrived just
  before a confirmation; this is visible and explainable from the snapshot. If the
  business wants retroactive tier top-ups, a later ADR adds a monthly true-up job
  (P16 adjustments).
