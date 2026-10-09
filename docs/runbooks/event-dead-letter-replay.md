# Operational Runbook: Event Dead-Letter Inspection & Replay

Procedures for inspecting parked events (`WAITING_DEPENDENCY`), troubleshooting dead-lettered events, and initiating idempotent replays (§8.4, §17.1).

---

## 1. Dead-Letter States & Causes

- `WAITING_DEPENDENCY`: Inbound event arrived before its required parent (e.g. `payment.refunded` before `payment.succeeded`). Retried automatically for up to 72 hours with exponential backoff.
- `DEAD_LETTER`: Event failed processing after all automatic retries exhausted, or unresolvable payload conflict occurred.

---

## 2. Inspection & Troubleshooting

1. Open Admin Panel > **Events Console** (`/events`).
2. Filter by status: `DEAD_LETTER`.
3. View `last_error` and `last_error_code`.
4. Inspect raw event body and verify whether dependent subscription or payment fact has now arrived.

---

## 3. Replay Procedure

1. Trigger replay from Admin UI button or via CLI / API:
   ```bash
   curl -X POST http://127.0.0.1:8000/v1/admin/events/{event_id}/replay \
     -H "Authorization: Bearer <ADMIN_JWT>"
   ```
2. Replay executes under the per-key advisory lock and updates state to `PROCESSED` or `IGNORED`.
3. Audit entry is automatically generated in `audit_logs`.
