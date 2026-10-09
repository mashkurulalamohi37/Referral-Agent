# Phase 0 Report: Design

- Date: 2026-10-08
- Exit criterion (§23): *docs reviewed; no contradictions left*.
- Status: **deliverables complete; waiting on review of the Proposed ADRs.**

## Built

| Deliverable (§23) | Location |
|---|---|
| ADRs | `docs/adr/` (22: 11 Accepted, 11 Proposed) |
| ERD | `docs/erd.md` (6 Mermaid diagrams by module, constraint table, tables added beyond §21) |
| OpenAPI draft | `docs/openapi.yaml` (OpenAPI 3.1: public, auth, service, me, ops, key admin routes); full admin route list in `docs/api.md` |
| Event JSON Schemas | `docs/events/*.schema.json` (envelope + 10 inbound types + 2 outbound), `docs/events.md` |
| Sequence diagrams | `docs/architecture.md`: Acceptance A (earn and reverse, with a worked ledger), B (credit), C (withdrawal), event state machine |
| Threat model | `docs/threat-model.md` (STRIDE across 6 trust boundaries, 9 referral abuse cases, residual risks) |
| Extra | `docs/api.md` (conventions, error-code registry), `tools/check_contracts.py`, `README.md` |

## Tests and checks

| Check | Result |
|---|---|
| `python tools/check_contracts.py`: 14 schemas valid Draft 2020-12 | Pass |
| 5 valid event examples accepted (incl. the ৳2,000 acceptance payment) | Pass |
| 5 invalid examples rejected, each for the intended reason: unknown health field (I9), float amount, credit without reservation id, non-UTC timestamp, chargeback without id | Pass |
| `openapi.yaml` validates as OpenAPI 3.1, including the `$ref` to the event envelope | Pass |
| All 12 Mermaid diagrams parse (rendered with mermaid 10.9.1) | Pass after fixing 2 (`;` inside sequence messages) |

No application code exists yet, so there is no unit test suite to run.

## Deviations from the spec

All are recorded in ADRs. The spec file itself is unchanged (ADR 0001).

| Spec | Change | ADR |
|---|---|---|
| §1/§23 MVP runs the acceptance scenario incl. withdrawal | Acceptance split into A (Phase 5), B (Phase 7), C (Phase 11) | 0004 |
| I2 "processed events never updated" vs event state machine | Immutable `inbound_events` + mutable `event_processing`; payloads in a purgeable table | 0006 |
| §10.2 posting table | Sign convention + complete table P1–P16 (adds credit refund, tax withholding, chargeback reinstate, late capture, payout return, write-off); new account `platform:tax_withholding_payable` | 0007 |
| §10.2 reversal source "available (or credit_only)" | Pro rata across the confirmation split; never touches reserved/payout_hold | 0008 |
| §12 `round(commission × refunded / net_paid)` | Cumulative, against cash collected (tax incl.) | 0009 |
| §9.4 lifecycle | Partial pending refunds, hold timing, `payment.failed` after success, chargeback reinstatement | 0010 |
| §8.3 `payment.chargeback` | + `chargeback_id`; new `payment.chargeback_resolved` | 0010 |
| §11 15-min TTL | 10-min release grace, synchronous capture, late capture P9; I5 scope clarified | 0011 |
| §8.4 per-subscription lock | Per product account | 0012 |
| §7.3 grace 60 min | 24 h + click-before-signup check + SDK durable retry | 0013 |
| §7.4 `EXPIRED` window | `conversion_window_days` (default 90) | 0014 |
| §15 visibility default `MASKED` | `NONE` for sensitive products (Healora) | 0016 |
| §18 `/public/products/{code}/theme` | `{slug}` | 0019 |
| §9.2 specificity | Bitmask score; ties prevented by a DB exclusion constraint | 0022 |
| §21 tables | + `auth_handoff_tokens`, `otp_challenges`, `kyc_submissions`, `chargebacks`, `commission_state_transitions`, `event_processing(_log)`, `inbound_event_payloads`, `ledger_adjustments`, `credit_refunds`, `reconciliation_runs`; `payout_approvals` → `approvals`; `outbound_webhooks` → `outbound_webhook_deliveries` | erd.md |
| §13 payout states | + `RETURNED` (provider bounce after paid, P14) | 0007 |
| — | New endpoint `POST /v1/reconciliation/payments` (Phase 13) | 0017 |

## Decisions needed from the business / reviewer

These ADRs are **Proposed**. Implementation will use them as defaults (like §24), but
each should be confirmed before the phase it blocks:

| ADR | Question | Blocks |
|---|---|---|
| 0013 | Is a 24 h attribution grace window acceptable (vs 60 min)? | Phase 3 |
| 0014 | Is 90 days the right signup → first-payment window? | Phase 3 |
| 0004 | Is "no cash withdrawal in MVP" acceptable? If not, a manual-only payout path moves into Phase 8. | Phase 5 |
| 0007 | Posting table and new `tax_withholding_payable` account (finance review) | Phase 5 |
| 0010 | Chargeback handling; products must send `chargeback_id` | Phase 5 |
| 0008, 0009 | Reversal allocation and refund proration (finance review) | Phase 6 |
| 0011 | Late capture can push a referrer negative when a product misbehaves | Phase 7 |
| 0016, 0020 | Healora visibility `NONE`; keep Quasar admin or switch to React | Phase 9 |
| 0017 | Daily reconciliation endpoint for products | Phase 13 |

## Open risks

1. **Real product contracts unknown.** PulsePOS/Healora must be able to emit
   `payment_id`, `refund_id`, `chargeback_id`, and UTC timestamps, and call capture
   synchronously. Worth confirming with each product team before Phase 8.
2. **Healora legal position** (Q12, ADR 0016) affects portal design in Phase 9.
3. **Local toolchain**: the dev machine has Python 3.13/3.14, not 3.12. All runtime and
   CI use the `python:3.12` Docker image, so this does not block Phase 1, but local
   non-Docker test runs should use 3.12 via `uv` or `pyenv-win` to avoid version drift.
4. **Two frontend stacks** (ADR 0020) remain a maintenance cost.

## Next: Phase 1 (Foundation)

Repo layout (§25), Compose (Postgres 16, Redis 7, API, worker, beat, Nginx), config,
structured logging with redaction, error envelope, `/health` and `/ready`, Alembic with
the `forbid_mutation` helper, CI (ruff, mypy --strict, pytest, `check_contracts.py`),
and the money, ID and clock utilities (ADR 0003) with full unit tests.
Exit: `docker compose up` healthy; CI green.
