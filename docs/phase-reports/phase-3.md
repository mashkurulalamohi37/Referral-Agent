# Phase 3 Report — Referrals & Attribution

**Date:** 2026-10-09  
**Status:** Completed ✅  
**Test Results:** 166 passed (100%), 0 failures, 14 JSON event schemas OK

---

## 1. Scope & Deliverables Completed

| Deliverable | Location | Status | Notes |
|---|---|---|---|
| Referral Models | `backend/app/referrals/models.py` | Complete | `ReferralCode`, `ReferralClick` (insert-only), `Attribution` with unique indexes |
| Referral Code Generation & Validation | `backend/app/referrals/service.py` | Complete | Crockford Base32-like alphabet (`23456789ABCDEFGHJKMNPQRSTUVWXYZ`), vanity checks, reserved words blacklist |
| Click Tracking & JWS Attribution Token | `backend/app/referrals/service.py` | Complete | SHA-256 privacy hashing of IP & User-Agent, signed cross-domain JWS token, strict redirect from registered product `signup_url` |
| Attribution Service & Rules | `backend/app/referrals/service.py` | Complete | Idempotency on `(product_id, external_user_id)`, self-referral rejection, 60m grace period check |
| Referrals & Attribution APIs | `backend/app/api/referrals.py` | Complete | `POST /v1/referrals/codes`, `GET /v1/referrals/codes`, `GET /v1/public/codes/{code}`, `GET /r/{code}`, `POST /v1/attributions` |
| Alembic Migration | `backend/migrations/versions/20261009_0003_referrals.py` | Complete | PostgreSQL 16 schema with `attach_forbid_mutation_trigger` for `referral_clicks` |
| Unit Test Suite | `backend/tests/unit/test_referrals.py` | Complete | 6 exhaustive security, collision, vanity, self-referral, and token tests |

---

## 2. Invariants & Security Rules Enforced

1. **Anti-Open Redirect Invariant (ADR 0001, §7.1)**:
   - Click redirect target URLs are strictly constructed using the registered product's `signup_url` stored in the database. Arbitrary redirect domains are impossible.
2. **Self-Referral Block (§7.3.1)**:
   - Self-referrals are prevented at multiple levels: user account ID matching, linked product account ownership, and email/phone identity checks (`ErrorCode.SELF_REFERRAL`).
3. **Idempotency & Precedence**:
   - `POST /v1/attributions` returns `201 Created (is_new=True)` on first ingestion and `200 OK (is_new=False)` on replay for `(product_id, external_user_id)`.
   - User-typed code wins precedence over cookie/token code when both are present.
4. **Insert-Only Clicks**:
   - `referral_clicks` table is protected by PostgreSQL 16 `forbid_mutation()` trigger to preserve unalterable click audit trail.

---

## 3. Verification

- `pytest backend/tests/unit` -> **166 passed in 9.45s**.
- `python tools/check_contracts.py` -> **14 schemas checked, OK**.
