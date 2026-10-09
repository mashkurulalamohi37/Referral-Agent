# Operational Runbook: Payout Disbursement & Maker-Checker Process

Operational procedure for reviewing, maker-checker approving, exporting, and settling monthly partner payouts (§13, §17.1).

---

## 1. Payout Review Workflow

1. **Finance Maker**:
   - Access **Admin Console > Payouts Review** (`/payouts`).
   - Review pending payouts under threshold or flagged for dual review.
   - Verify partner KYC status and confirm zero open HIGH risk cases.
2. **Finance Checker (Distinct Admin)**:
   - Second finance officer logs in and executes `Approve` on requests exceeding `dual_approval_threshold`.
   - The database constraint `approved_by <> requested_by` strictly prevents single-actor bypass.

---

## 2. Bulk CSV Export & Bank / MFS Upload

1. Export approved batch:
   ```bash
   curl -s http://127.0.0.1:8000/v1/payouts/export/csv \
     -H "Authorization: Bearer <FINANCE_ADMIN_JWT>" > payouts_batch_$(date +%Y%m%d).csv
   ```
2. Upload CSV to corporate banking portal or bKash / Nagad merchant disbursement portal.
3. Once batch clears, enter transfer references into platform via `/v1/payouts/{id}/mark-paid` to trigger P10 ledger clearing.
