# 0009. Cumulative refund proration

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 6

## Context

§12 reverses commission as `round(commission × refunded / net_paid)`. Two problems:

1. `amount_refunded` is what the product returned to the customer, which normally
   includes tax. `amount_net_paid` excludes tax and referral credit (§9.3). A full
   refund of a taxed payment gives a ratio above 1.
2. Rounding each partial refund separately drifts: three refunds of a third each can
   reverse 1 minor unit more or less than the commission.

## Decision

- Define **`cash_collected = amount_gross − discount_amount − credit_applied_amount`**
  for the payment (tax included: it is what the customer actually paid in cash).
- On each refund, compute **cumulatively**:

```text
cum_refunded   = sum of all refunds for the payment so far (including this one)
ratio          = min(1, cum_refunded / cash_collected)            -- Decimal
target_reversed = round_half_up(commission_amount × ratio)
this_reversal  = target_reversed − already_reversed
```

- A refund that brings `cum_refunded` to `cash_collected` reverses exactly the remaining
  commission. Cumulative reversals never exceed the commission.
- If `cash_collected == 0` (fully paid by credit/discount) there is no commission (base
  is 0), so refunds only trigger the credit-refund path (§12, P10).
- Refunds above `cash_collected` are accepted, recorded, and logged as an anomaly; they
  reverse nothing extra.
- The calculation (inputs, ratio, rounding) is stored on the `commission_reversals` row
  as `calculation_snapshot`, like I8.

## Consequences

- Full refunds always reverse 100% of the commission regardless of tax.
- Partial refunds are proportional to cash collected, so tax is reversed in proportion,
  which matches how products refund.
