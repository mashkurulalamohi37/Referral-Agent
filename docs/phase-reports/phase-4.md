# Phase 4 Report — Inbound Events, Outbox & Subscriptions

**Date:** 2026-10-09  
**Status:** Completed ✅  
**Test Results:** 170 passed (100%), 0 failures, 14 JSON event schemas OK

---

## 1. Scope & Deliverables Completed

| Deliverable | Location | Status | Notes |
|---|---|---|---|
| Event Models | `backend/app/events/models.py` | Complete | `InboundEvent` (insert-only), `OutboxMessage` |
| Subscription Models | `backend/app/subscriptions/models.py` | Complete | `Subscription`, `PaymentFact` (insert-only), `RefundFact` (insert-only) |
| Event Schema Validation | `backend/app/events/service.py` | Complete | Draft202012Validator preloaded with referencing.Registry for all 14 official schemas |
| HMAC Signature & Replay Protection | `backend/app/events/service.py` | Complete | Constant-time HMAC-SHA256 verification and 300s timestamp drift check (§8.1) |
| Ingestion & Idempotency | `backend/app/events/service.py` | Complete | Idempotency on `(product_id, event_id)`, SHA-256 payload conflict check, business key conflict prevention |
| Subscriptions Service | `backend/app/subscriptions/service.py` | Complete | Derived subscription state machine & immutable payment/refund facts |
| Event Intake API | `backend/app/api/events.py` | Complete | `POST /v1/events` returning `202 Accepted` for new and `200 OK` for duplicate |
| Alembic Migration | `backend/migrations/versions/20261009_0004_events_and_subscriptions.py` | Complete | PostgreSQL 16 schema with `attach_forbid_mutation_trigger` for `inbound_events`, `payment_facts`, `refund_facts` |
| Unit Test Suite | `backend/tests/unit/test_events_and_subscriptions.py` | Complete | Signature drift, schema validation, idempotency, and business key conflict tests |

---

## 2. Invariants & Security Rules Enforced

1. **Replay & Timestamp Invariant (§8.1)**:
   - Inbound events must supply `X-Signature-Timestamp` within 300 seconds of current platform clock (`ErrorCode.SIGNATURE_TIMESTAMP_STALE`).
2. **Deterministic Payload Idempotency (§8.4)**:
   - Replaying the same `(product_id, event_id)` with an identical raw payload hash returns `200 OK` (`is_new=False`, `status="DUPLICATE"`).
   - Reusing an existing `event_id` with a different payload immediately raises `ErrorCode.EVENT_ID_CONFLICT` (`409 Conflict`).
3. **Cross-Event Business Key Integrity**:
   - `payment.succeeded` verifies `(product_id, payment_id)` has not been recorded previously under another `event_id` (`ErrorCode.BUSINESS_KEY_CONFLICT`).
4. **Transactional Outbox (ADR 0006)**:
   - `OutboxMessage` is persisted in the exact same DB transaction as `InboundEvent` and derived domain facts.

---

## 3. Verification

- `pytest backend/tests/unit` -> **170 passed in 9.38s**.
- `python tools/check_contracts.py` -> **14 schemas checked, OK**.
