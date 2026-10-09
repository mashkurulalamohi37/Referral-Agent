# Phase 5 Report — Commission Engine & Double-Entry Ledger Engine

**Date:** 2026-10-09  
**Status:** Completed ✅  
**Test Results:** 174 passed (100%), 0 failures, 14 JSON event schemas OK

---

## 1. Scope & Deliverables Completed

| Deliverable | Location | Status | Notes |
|---|---|---|---|
| Commission Models | `backend/app/commissions/models.py` | Complete | `CommissionRule` (versioned), `Commission` lifecycle |
| Ledger Models | `backend/app/ledger/models.py` | Complete | `LedgerAccount`, `JournalTransaction` (insert-only), `LedgerEntry` (insert-only) |
| Specificity Scoring Engine | `backend/app/commissions/service.py` | Complete | Deterministic bitmask scoring per ADR 0022 and tie detection (`ErrorCode.COMMISSION_RULE_TIE`) |
| Integer Money Math | `backend/app/commissions/service.py` | Complete | Zero floats; exact integer poisha arithmetic via `apply_bps` and `allocate` (Invariant I3) |
| Double-Entry Postings (P1–P4) | `backend/app/ledger/service.py` | Complete | Enforces Invariant I1 (`sum(entries.amount) == 0`); balance aggregation per partner bucket |
| Commission Lifecycle & Batch | `backend/app/commissions/service.py` | Complete | `PENDING` -> `AVAILABLE` (14 days) -> `REVERSED` / `CANCELLED` |
| Commissions & Ledger APIs | `backend/app/api/commissions.py`, `ledger.py` | Complete | `/v1/commissions`, `/v1/admin/rules`, `/v1/wallet/me` |
| Alembic Migration | `backend/migrations/versions/20261009_0005_commissions_and_ledger.py` | Complete | PostgreSQL 16 schema with `attach_forbid_mutation_trigger` for `journal_transactions` & `ledger_entries` |
| Acceptance Scenario A Tests | `backend/tests/unit/test_commissions_and_ledger.py` | Complete | End-to-end verification of Rahim/Karim/Healora scenario (§1) |

---

## 2. Invariants & Acceptance Scenario Verified

1. **Acceptance Scenario A (§1 Verified)**:
   - Rahim enrolls as partner -> code `RAHIM82`.
   - Karim clicks `/r/RAHIM82?product=healora` -> attribution recorded.
   - Karim pays ৳2,000 (200,000 poisha) -> 10% rule resolved -> ৳200 (20,000 poisha) commission created as `PENDING`.
   - Double-entry ledger posted: Debit `platform:commission_expense:BDT` (+20000), Credit `user:pending:rahim:BDT` (-20000).
   - Confirmation period passes (14 days) -> `confirm_commission` moves commission to `AVAILABLE`.
   - Ledger posted: Debit `user:pending:rahim:BDT` (+20000), Credit `user:available:rahim:BDT` (-20000).
   - Rahim wallet available balance is exactly ৳200 (20,000 poisha).
2. **Double-Entry Balance Invariant I1**:
   - Posting an unbalanced transaction immediately aborts with `ErrorCode.LEDGER_UNBALANCED`.
3. **No Float Arithmetic Invariant I3**:
   - Money calculations use integer minor units and single `ROUND_HALF_UP` without float division.
4. **Specificity Scoring & Tie Prevention (ADR 0022)**:
   - Exact rank: `partner_id` (128) > `campaign_id` (64) > `partner_type` (32) > `plan_code` (16) > `billing_reason` (8) > `product_id` (4) > priority.

---

## 3. Verification

- `pytest backend/tests/unit` -> **174 passed in 10.82s**.
- `python tools/check_contracts.py` -> **14 schemas checked, OK**.
