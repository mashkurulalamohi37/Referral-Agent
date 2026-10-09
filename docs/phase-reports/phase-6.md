# Phase 6 Report — Refunds, Renewals, and Recurring Commissions

**Date:** 2026-10-09  
**Status:** Completed ✅  
**Test Results:** 177 passed (100%), 0 failures, 14 JSON event schemas OK

---

## 1. Scope & Deliverables Completed

| Deliverable | Location | Status | Notes |
|---|---|---|---|
| Proportional Refund Reversals | `backend/app/commissions/service.py` | Complete | `process_refund_reversal` with exact integer math `mul_div_round` |
| Cumulative Refund Tracking | `backend/app/subscriptions/service.py` | Complete | `get_total_refunded_for_payment` computes cumulative refund totals |
| Negative Balance & Clawback Policy | `backend/app/ledger/service.py`, `commissions/service.py` | Complete | ADR 0009: debit available balance into negative; clawback on future commissions |
| Renewal Window Eligibility | `backend/app/commissions/service.py` | Complete | `eligible_months_from_conversion` restricts recurring attribution window |
| Plan Upgrades & Net Invoicing | `backend/app/commissions/service.py` | Complete | Positive net upgrade commissions computed on net amount |
| Acceptance Scenario B & C Tests | `backend/tests/unit/test_refunds_and_renewals.py` | Complete | End-to-end unit tests covering partial refunds, ledger postings, renewal cutoff, and upgrades |

---

## 2. Invariants & Acceptance Scenarios Verified

1. **Acceptance Scenario B (Partial Refund & Proportional Reversal §1 Verified)**:
   - Karim pays ৳2,000 (200,000 poisha) -> Rahim receives ৳200 commission.
   - Karim requests 50% partial refund of ৳1,000 (100,000 poisha).
   - Platform calculates proportional reversal: `20000 * 100000 / 200000 = 10000` poisha (৳100).
   - Ledger reversal posting:
     - Debit `user:available:rahim:BDT` (+10000)
     - Credit `platform:commission_expense:BDT` (-10000)
   - Final available balance correctly reflects remaining ৳100.
2. **Negative Balance & Clawback (ADR 0009)**:
   - If a reversal occurs when Rahim's available balance is 0, his balance drops to -৳100.
   - Subsequent commissions offset the negative balance automatically before funds become withdrawable.
3. **Acceptance Scenario C (Renewal Eligibility Window §1 Verified)**:
   - Subscription renewal event at month 3 is within the 12-month window -> recurring commission generated.
   - Subscription renewal event at month 15 is outside the 12-month window -> skipped (0 commission).
4. **Plan Upgrades / Downgrades**:
   - Prorated net invoice upgrade generates commission strictly on the positive net charged amount.

---

## 3. Verification

- `pytest backend/tests/unit` -> **177 passed in 11.36s**.
- `python tools/check_contracts.py` -> **14 schemas checked, OK**.
