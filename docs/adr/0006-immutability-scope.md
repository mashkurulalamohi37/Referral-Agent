# 0006. Immutability scope: insert-only tables vs processing state

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 1

## Context

I2 says ledger entries, journal transactions, audit logs and processed events are never
updated or deleted. But §8.4 gives inbound events a state machine
(`RECEIVED → PROCESSING → …`), and §21 gives every table `created_at` **and**
`updated_at`, including insert-only tables.

## Decision

**Insert-only tables** (DB trigger raises on `UPDATE`, `DELETE`, `TRUNCATE`): `ledger_entries`,
`journal_transactions`, `audit_logs`, `inbound_events`, `commission_reversals`,
`commission_state_transitions`, `risk_signals`.
These have `created_at` only, no `updated_at`.

**Inbound events are split in two:**
- `inbound_events`: immutable facts — product, `event_id`, type, schema version,
  `occurred_at`, raw body (JSONB), body SHA-256, `received_at`, api client.
- `event_processing`: one row per inbound event, mutable — `state`, `attempts`,
  `next_attempt_at`, `last_error_code`, `last_error`, `processed_at`, `outcome`.
  State history is appended to `event_processing_log` (insert-only).

**Commission state** changes in `commissions.state` (mutable row), and every transition
is appended to `commission_state_transitions` (insert-only) with actor and reason.

**Trigger**: one shared function `forbid_mutation()` installed by an Alembic helper
`make_insert_only(table)`. The migration test suite asserts every table on the
insert-only list has the trigger.

## Consequences

- I2 is literally true for the listed tables; operational state lives elsewhere.
- Erasure (§15) never touches insert-only tables; those reference pseudonymous IDs only.
- Retention purge of `inbound_events.raw_body` (24 months, §15) cannot be an `UPDATE`.
  Raw bodies are stored in a separate `inbound_event_payloads` table that is **not**
  insert-only and may be deleted by the retention job only. `inbound_events` keeps the
  body hash, so idempotency (`409 EVENT_ID_CONFLICT`) still works after purge.
