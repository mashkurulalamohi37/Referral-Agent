# 0008. Reversal allocation across split rewards and held funds

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 6

## Context

§10.2 says an available commission is reversed from "`user:available` (or
`credit_only`)". With `reward_split = {"WALLET": 50, "CREDIT_ONLY": 50}` the split of a
reversal is undefined. It is also undefined what happens when the funds have moved on
to `user:reserved` or `user:payout_hold`.

## Decision

1. A reversal of an AVAILABLE commission is allocated across the accounts credited by
   that commission's P2 confirmation posting, **in the same proportions**, using
   `money.allocate` (largest remainder). Example: confirmed 200 → available 100,
   credit_only 100; reversal of 75 → available 38, credit_only 37
   (remainder goes to the larger fractional part; ties go to `available`).
2. Reversals always debit `user:available` / `user:credit_only`, never `user:reserved`
   or `user:payout_hold`. Open reservations and withdrawal requests are not disturbed.
   The source accounts may go negative (§10.4).
3. If a reversal makes the user `negative` (ADR 0007), then in the same transaction:
   - pending withdrawal requests in `REQUESTED` / `UNDER_REVIEW` are flagged
     `NEEDS_REVIEW` (not auto-cancelled), and approval is blocked while negative;
   - open credit reservations are left to capture or expire normally.
4. Reversals of a PENDING commission debit `user:pending` only (P3).

## Consequences

- Reversals are deterministic and reproducible from the commission's confirmation
  posting.
- A user can briefly hold funds in reservation while negative; this is bounded by the
  reservation TTL and the per-invoice cap.
