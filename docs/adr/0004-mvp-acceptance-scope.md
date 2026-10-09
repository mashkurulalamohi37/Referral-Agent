# 0004. MVP acceptance scenario stops before withdrawal

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 5

## Context

§1's acceptance scenario ends with "Rahim … can withdraw it". §23 says the MVP
(Phases 0–8) is the smallest system that runs the acceptance scenario, and Phase 5's exit
criterion is the acceptance scenario end-to-end. But payouts are Phase 11, payout
eligibility needs KYC (portal, Phase 9) and a risk check (Phase 12). The phase plan
cannot satisfy its own exit criterion.

Options:

1. Move a minimal payout path into the MVP.
2. Split the acceptance scenario: the MVP proves earning and spending; withdrawal is
   proven in Phase 11.

## Decision

Option 2.

- **Acceptance A (Phase 5 exit, MVP):** enroll → click → attribution → payment →
  PENDING → AVAILABLE → refund reverses with new ledger entries. Balance is
  queryable through `GET /v1/me/wallet` and the ledger.
- **Acceptance B (Phase 7 exit, MVP):** Rahim's available balance is reserved and
  captured as subscription credit on a connected product; reserve → payment fail →
  release returns the funds.
- **Acceptance C (Phase 11 exit):** Rahim withdraws via the manual provider; ledger
  postings match ADR 0007.
- The withdrawal ledger postings (`requested`, `paid`, `rejected`) are still
  implemented and property-tested in Phase 5 at the ledger level, because the posting
  table is part of the ledger module.

## Consequences

- The MVP shows referrers their balance and lets them spend it as credit; it does not
  pay cash. If cash withdrawal is required at MVP launch, choose option 1 and pull a
  manual-provider-only payout path (no KYC upload, admin-verified KYC flag) into
  Phase 8.
