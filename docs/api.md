# API Conventions and Error Registry

Contract: [`openapi.yaml`](openapi.yaml) (draft until Phase 2 generates it from code; from
then on the generated `/openapi.json` is authoritative and CI diffs it against this
file's paths). Events: [`events.md`](events.md).

## Conventions

| Topic | Rule |
|---|---|
| Base path | `/v1` (gateway may expose `/api/v1`) |
| Success body | The resource itself. Lists: `{ "items": [...], "next_cursor": "…" \| null }` |
| Error body | `{ "success": false, "error": { "code", "message", "request_id", "details" } }` |
| Pagination | Cursor, `?cursor=&limit=`, `limit` default 25, max 100. Cursors are opaque, signed, and encode `(sort_key, id)` |
| Money | Integer minor units + `currency`. Field names without suffix in the API (`amount`), `_minor` suffix in the DB |
| Time | RFC 3339 UTC in the API. Inbound event timestamps must be UTC (`Z` / `+00:00`) |
| Idempotency | `Idempotency-Key` header required on non-event POSTs that move money (capture, release, payout request, admin approvals, adjustments). Stored 7 days per (caller, key, route) with a body hash; same key + different body → `409 IDEMPOTENCY_KEY_REUSED`. Reservation and credit-refund requests carry the key in the body (§11) |
| Request ID | `X-Request-ID` accepted (validated, max 64 chars) or generated; echoed on every response and in every log line |
| Unknown fields | Rejected (`extra="forbid"`) → `422 VALIDATION_ERROR` with the field path in `details` |
| Rate limits | `429 RATE_LIMITED` with `Retry-After`. Per API client on service routes, per IP on public routes |
| Docs | `/openapi.json`, `/docs`, `/redoc`; disabled or admin-auth-only in production |

## HTTP status usage

`200` read / idempotent replay · `201` created · `202` accepted for async processing ·
`204` no content · `400` malformed (bad JSON, bad signature header format) · `401`
authentication · `403` authenticated but not permitted (scope, role, cross-product) ·
`404` not found (also used for resources of another product, never `403`, to avoid
leaking existence) · `409` conflict with current state · `422` well-formed but rejected
by business rules or validation · `429` rate limited · `503` not ready.

## Error code registry

Codes are stable; messages may change. New codes are added here in the same PR as the
code that raises them (CI checks every `raise PlatformError("…")` code appears here).

### General

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Schema validation failed; `details.errors[]` has `loc`, `msg` |
| `NOT_FOUND` | 404 | Resource does not exist or is not visible to the caller |
| `METHOD_NOT_ALLOWED` | 405 | Route exists but not for this HTTP method |
| `MALFORMED_REQUEST` | 400 | Body is not valid JSON or a header is malformed |
| `RATE_LIMITED` | 429 | Too many requests |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | Missing `Idempotency-Key` on a money-moving POST |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Same key used with a different request body |
| `CONFLICT` | 409 | Generic state conflict (prefer a specific code) |
| `INTERNAL_ERROR` | 500 | Unexpected; no stack trace in production |
| `SERVICE_UNAVAILABLE` | 503 | Dependency down |

### Auth

| Code | HTTP | Meaning |
|---|---|---|
| `AUTH_REQUIRED` | 401 | No credentials |
| `AUTH_INVALID_CREDENTIALS` | 401 | Wrong key, password, OTP or TOTP |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token expired |
| `AUTH_REFRESH_REUSED` | 401 | Rotated refresh token reused; family revoked |
| `AUTH_HANDOFF_INVALID` | 401 | Handoff token unknown, expired or already used |
| `AUTH_TOTP_REQUIRED` | 401 | Admin role requires TOTP |
| `API_CLIENT_REVOKED` | 401 | Client or secret revoked |
| `SCOPE_MISSING` | 403 | Client lacks the scope for this route |
| `PERMISSION_DENIED` | 403 | Role lacks permission |
| `MAKER_CHECKER_SAME_ACTOR` | 403 | Approver is the requester |

### Events

| Code | HTTP | Meaning |
|---|---|---|
| `SIGNATURE_INVALID` | 401 | HMAC mismatch |
| `SIGNATURE_TIMESTAMP_STALE` | 401 | Timestamp outside ±300 s |
| `EVENT_ID_CONFLICT` | 409 | Same `event_id`, different body |
| `EVENT_TYPE_UNSUPPORTED` | 422 | Unknown `event_type` or `schema_version` |
| `AMOUNT_INCONSISTENT` | 422 | `amount_net_paid` ≠ gross − discount − tax − credit |
| `CURRENCY_NOT_ENABLED` | 422 | Currency not enabled (v1: BDT only) |
| `BUSINESS_KEY_CONFLICT` | 409 | Same `payment_id`/`refund_id`/`chargeback_id` with different content under a new `event_id` |
| `EVENT_NOT_REPLAYABLE` | 409 | Replay requested for an event not in `DEAD_LETTER`/`FAILED` |

Event processing outcomes (not HTTP errors; stored in `event_processing.outcome_code`):
`NOT_REFERRED`, `REFERRAL_EXPIRED`, `REFERRAL_INACTIVE`, `OUTSIDE_RENEWAL_WINDOW`,
`MAX_PAYMENTS_REACHED`, `BELOW_MINIMUM`, `ZERO_COMMISSION`, `NO_MATCHING_RULE`,
`RULE_TIE_NEEDS_REVIEW`, `DEPENDENCY_MISSING`, `DUPLICATE_BUSINESS_KEY`.

### Referrals and attribution

| Code | HTTP | Meaning |
|---|---|---|
| `REFERRAL_CODE_INVALID` | 422 | Unknown, inactive or not valid for this product |
| `REFERRAL_CODE_REQUIRED` | 422 | Product requires a code (Q15) |
| `REFERRAL_CODE_TAKEN` | 409 | Vanity code exists |
| `REFERRAL_CODE_FORBIDDEN` | 422 | Reserved word or profanity |
| `ATTRIBUTION_TOKEN_INVALID` | 422 | Bad JWS, wrong product, or code mismatch where no typed code exists |
| `ATTRIBUTION_TOKEN_EXPIRED` | 422 | Outside attribution window |
| `ATTRIBUTION_NOT_NEW_ACCOUNT` | 422 | Outside grace, prior payment, or click after signup (ADR 0013) |
| `ATTRIBUTION_TIMESTAMP_INVALID` | 422 | `registered_at` in the future |
| `ATTRIBUTION_LOCKED` | 409 | Admin change after first commission became AVAILABLE |
| `SELF_REFERRAL` | 422 | Referrer would earn from their own account |
| `REFERRER_BLOCKED` | 422 | Referrer is BLOCKED by risk |

### Commissions and rules

| Code | HTTP | Meaning |
|---|---|---|
| `COMMISSION_RULE_TIE` | 409 | Rule would tie with an active rule (ADR 0022) |
| `COMMISSION_RULE_INVALID` | 422 | Inconsistent fields (e.g. TIERED without schedule, split ≠ 100) |
| `COMMISSION_STATE_INVALID` | 409 | Transition not allowed from current state |

### Ledger, credits, payouts

| Code | HTTP | Meaning |
|---|---|---|
| `CREDIT_ACCOUNT_NOT_LINKED` | 404 | Product account is not linked to a referrer |
| `CREDIT_CROSS_PRODUCT_DISABLED` | 422 | Product does not accept cross-product credit |
| `RESERVATION_ALREADY_CAPTURED` | 409 | Release after capture |
| `RESERVATION_ALREADY_RELEASED` | 409 | Informational; capture still succeeds as late capture (ADR 0011) |
| `CREDIT_REFUND_EXCEEDS_CAPTURED` | 422 | Cumulative credit refunds would exceed capture |
| `INSUFFICIENT_BALANCE` | 422 | Payout or adjustment exceeds available |
| `BALANCE_NEGATIVE` | 422 | Withdrawals blocked while negative |
| `PAYOUT_NOT_ELIGIBLE` | 422 | `details.reasons[]`: `EMAIL_UNVERIFIED`, `PHONE_UNVERIFIED`, `KYC_REQUIRED`, `BELOW_MIN_PAYOUT`, `ABOVE_MAX_PAYOUT`, `MONTHLY_LIMIT`, `RISK_CASE_OPEN` |
| `PAYOUT_STATE_INVALID` | 409 | Transition not allowed |
| `LEDGER_UNBALANCED` | 500 | Defensive: posting rejected by I1 check (alerts) |

## Admin endpoints (full list, §20)

All under `/v1/admin`, `userJwt` with role permissions from the central permission map.
Every write is audited. Money-affecting writes require `Idempotency-Key`.

| Resource | Endpoints |
|---|---|
| users | `GET /users`, `GET /users/{id}`, `POST /users/{id}/roles`, `DELETE /users/{id}/roles/{role}`, `POST /users/{id}/suspend`, `POST /users/{id}/erase` |
| partners | `GET /partners`, `POST /partners/{id}/approve`, `POST /partners/{id}/reject`, `POST /partners/{id}/kyc/{submission_id}/decision` |
| products | `GET/POST /products`, `GET/PATCH /products/{id}` |
| plans | `GET/POST /plans`, `PATCH /plans/{id}` |
| api-clients | `GET/POST /api-clients`, `POST /api-clients/{id}/rotate`, `POST /api-clients/{id}/revoke` |
| codes | `GET /codes`, `POST /codes/{code}/approve`, `POST /codes/{code}/reject`, `POST /codes/{code}/deactivate` |
| campaigns | `GET/POST /campaigns`, `PATCH /campaigns/{id}` |
| commission-rules | `GET/POST /commission-rules`, `GET /commission-rules/{rule_id}`, `POST /commission-rules/{rule_id}/versions`, `POST /commission-rules/{rule_id}/close`, `POST /commission-rules/simulate` |
| referrals | `GET /referrals`, `GET /referrals/{id}`, `POST /referrals/{id}/reassign`, `POST /referrals/{id}/revoke`, `POST /attributions` (admin attribution of existing customers) |
| commissions | `GET /commissions`, `GET /commissions/{id}`, `POST /commissions/{id}/hold`, `POST /commissions/{id}/release-hold`, `POST /commissions/{id}/reject` |
| wallets / ledger | `GET /wallets/{user_id}`, `GET /ledger/transactions`, `GET /ledger/transactions/{id}`, `POST /ledger/adjustments`, `POST /ledger/adjustments/{id}/approve` |
| reservations | `GET /reservations`, `GET /reservations/{id}` |
| payouts | `GET /payouts`, `GET /payouts/{id}`, `POST /payouts/{id}/approve`, `POST /payouts/{id}/reject`, `POST /payouts/{id}/mark-paid`, `POST /payouts/{id}/mark-failed`, `GET /payouts/export.csv` |
| risk-cases | `GET /risk-cases`, `GET /risk-cases/{id}`, `POST /risk-cases/{id}/assign`, `POST /risk-cases/{id}/notes`, `POST /risk-cases/{id}/decision` |
| events | `GET /events`, `GET /events/{id}`, `POST /events/{id}/replay` |
| templates | `GET/POST /templates`, `POST /templates/{id}/versions`, `POST /templates/{id}/preview` |
| reports | `GET /reports/{name}`, `GET /reports/{name}/export.csv`, `GET /dashboard` |
| audit-logs | `GET /audit-logs`, `GET /audit-logs/export.csv` |
| settings | `GET /settings`, `PUT /settings/{key}` (new version) |
