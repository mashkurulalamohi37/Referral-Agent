# 0010. Commission lifecycle gaps: partial pending refunds, holds, failures, chargebacks

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 5

## Context

The §9.4 diagram leaves out: the state after a partial refund of a PENDING commission;
whether ON_HOLD time counts toward confirmation; what `payment.failed` means for a
payment that has a commission; and how a won chargeback is handled. §8.3's
`payment.chargeback` has no chargeback ID and there is no resolution event.

## Decision

### States

```text
PENDING ──(eligible_at reached, no hold)───────────────► AVAILABLE
PENDING ──(risk HIGH / manual hold)──► ON_HOLD
ON_HOLD ──(cleared, now ≥ eligible_at)───────────────► AVAILABLE
ON_HOLD ──(cleared, now < eligible_at)───────────────► PENDING
ON_HOLD ──(rejected by analyst)──────────────────────► REJECTED      (P3 full)
PENDING / ON_HOLD ──(cumulative reversal = 100%)─────► CANCELLED     (P3)
AVAILABLE ──(partial reversal)───────────────────────► PARTIALLY_REVERSED (P4)
AVAILABLE / PARTIALLY_REVERSED ──(reversal to 100%)──► REVERSED      (P4)
REVERSED / PARTIALLY_REVERSED ──(chargeback won)─────► AVAILABLE or PARTIALLY_REVERSED (P5)
```

- **Partial refund of a PENDING or ON_HOLD commission** keeps the state and reduces the
  pending amount (P3). Columns: `amount_minor` (original, immutable after creation),
  `reversed_minor` (cumulative), and `outstanding = amount − reversed`.
  On confirmation, P2 posts `outstanding`.
- **Confirmation clock**: `eligible_at = paid_at + confirmation_days` (Q2: max(14 days,
  product refund window)). Time on hold counts. A hold only blocks the transition.
- **Terminal states**: `CANCELLED`, `REJECTED`, `REVERSED` (but `REVERSED` can be
  reinstated by a won chargeback only).

### `payment.failed`

- For a payment with no `payment.succeeded` recorded: stored as a fact, no commission
  effect.
- For a payment already recorded as succeeded (a product correction): treated as a full
  refund of that payment with `source_ref = payment-failed:{payment_id}`, and logged as
  an anomaly for review.

### Chargebacks (event contract change)

- `payment.chargeback` gains required `chargeback_id`; business key
  `(product_id, chargeback_id)` is unique.
- New event `payment.chargeback_resolved` with `chargeback_id`, `outcome`
  (`won` | `lost`), `resolved_at`.
- On `payment.chargeback`: reverse the full outstanding commission (P3/P4,
  `source_ref = chargeback:{id}`) and emit a risk signal `CHARGEBACK`.
- On `won`: reinstate exactly what that chargeback reversed (P5). On `lost`: no ledger
  effect; record the outcome.

## Consequences

- Every lifecycle path has a defined state and posting; `commission_state_transitions`
  records each one.
- Products must send `chargeback_id`. The SDK's typed event builder makes it required.
