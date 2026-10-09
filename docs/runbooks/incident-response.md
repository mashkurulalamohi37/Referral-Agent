# Operational Runbook: Security & Incident Response

Protocols for handling security incidents, compromised API secrets, corrupted signatures, and ledger reconciliation imbalances (§22).

---

## 1. API Client Secret Compromise & Rotation

1. **Immediate Revocation**:
   - Navigate to **Admin Panel > API Clients**.
   - Create new active secret pair (`key_id`, `secret`, `signing_secret`).
   - Retire the old secret (transitions status to `RETIRED` with a 24-hour grace window, or `REVOKED` for instant cutoff).
2. **Audit Verification**:
   - Verify `audit_logs` table for unauthorized actions using the compromised client key.

---

## 2. Ledger Imbalance Alert (`LEDGER_UNBALANCED`)

1. **Trigger Condition**: Sentry alert or exception `PlatformError(ErrorCode.LEDGER_UNBALANCED)` indicates sum of journal entries != 0.
2. **Investigation**:
   - Check `journal_transactions` table for the failing `idempotency_key`.
   - Verify calculation rounding and input amounts.
   - Note: Database deferred constraint trigger prevents any unbalanced entry from committing.

---

## 3. High Risk Fraud Outbreak

1. Analyst sets affected referrer or referral status to `BLOCKED`.
2. Blocked status immediately suspends attribution, halts commission confirmation, and freezes pending payout requests.
