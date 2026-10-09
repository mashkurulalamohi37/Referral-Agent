# Centralized Referral & Commission Platform: Implementation Spec v2

> **How to use this document.** This is the build brief for an AI coding agent or an engineering team. Section 0 says how to work. Sections 1–22 define *what* to build and the rules it must follow. Section 23 is the phased delivery plan with exit criteria. Section 24 lists open business questions, each with a default to use until the business decides.

---

## 0. Working Instructions (read first)

1. **Build in phases (Section 23).** At the end of each phase, stop. Run the full test suite. Write a short phase report: what was built, test results, deviations from this spec, and open risks. Do not start the next phase until the current phase's exit criteria pass.
2. **Record decisions.** Every non-trivial design decision goes in `docs/adr/NNNN-title.md` (context, decision, consequences). When this spec is ambiguous, use the default in Section 24, then write an ADR.
3. **No stubs in money paths.** Commission, ledger, credit, refund and payout code must be complete and tested. Never use `TODO`, mock math or placeholder logic there. Non-financial features may be stubbed behind an interface if the phase says so.
4. **Never invent integration details** for PulsePOS, Healora, System 3 or System 4. Integrate through the generic contract in Section 8. Use the **product simulator** (Section 19.3) to stand in for real products.
5. **The invariants in Section 4 are non-negotiable.** If an implementation choice would violate one, stop and raise it.

---

## 1. Goal and Scope

**Goal.** A standalone platform that owns referral attribution, commission calculation, the wallet ledger, subscription credit and payouts for any number of SaaS products. Products connect only through signed APIs and events. Products never calculate commission.

**Acceptance scenario (must work end-to-end):**

```text
Rahim enrolls as a referrer → gets code RAHIM7K3Q (or approved vanity code RAHIM82)
Karim opens ref.example.com/r/RAHIM82?product=healora
  → click recorded → redirect to Healora signup with a signed attribution token
Karim signs up on Healora → Healora backend calls POST /v1/attributions
  → Karim's Healora account is attributed to Rahim
Karim pays ৳2,000 for Healora Premium → Healora sends payment.succeeded
  → rule resolved (10%) → ৳200 commission PENDING (ledger posted)
Confirmation period passes, no refund, no risk hold
  → commission AVAILABLE (ledger posted)
Rahim sees ৳200 available and can withdraw it, reserve it as subscription
  credit on a connected product, or keep it.
If Karim is refunded → commission reversed with new ledger entries (never edits).
```

**In scope:** everything in Sections 2–22.

**Out of scope for v1:**

- Processing customer payments (products do this).
- Real payout gateway integrations. Build the provider interface plus a manual provider.
- Multi-level (MLM) commissions. Design the schema for it, keep it disabled, build no UI.
- Native mobile apps.

---

## 2. Locked Technical Decisions

| Area | Decision |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x (async, `asyncpg`), Alembic |
| Architecture | **Modular monolith.** One deployable API image, one worker image. Strict module boundaries (Section 3). No separate microservices in v1. |
| Database | PostgreSQL 16, single source of truth |
| Cache / broker | Redis 7 |
| Background jobs | Celery + Celery Beat. All tasks idempotent. How tasks access the DB (sync engine vs async wrapper) is decided in an ADR. |
| Reliable side effects | **Transactional outbox.** Notifications, outbound webhooks and follow-up jobs are written to an `outbox` table in the same DB transaction as the business change, then dispatched by a worker. |
| Money | Integer **minor units** (`BIGINT`, e.g. poisha for BDT) plus ISO-4217 `currency`. Python `Decimal` for intermediate math. Never `float`. Rounding: `ROUND_HALF_UP` to the minor unit, applied once at the end of a calculation. |
| Time | All timestamps `timestamptz` in UTC. UI displays in the user's time zone (default `Asia/Dhaka`). |
| IDs | UUIDv7 primary keys |
| Customer portal | React 18 + TypeScript + Vite, React Router, TanStack Query, React Hook Form + Zod |
| Admin panel | Quasar 2 / Vue 3 Composition API + TypeScript, Pinia, Vue Router |
| Gateway | Nginx (TLS termination, routing, basic rate limits) |
| Local / deploy | Docker, Docker Compose (`docker-compose.yml` base, `.dev.yml` and `.prod.yml` overrides) |
| Lint / type | `ruff`, `mypy --strict` (backend); `eslint`, `tsc --noEmit` (frontends) |

> Two frontend stacks (React and Quasar) double UI maintenance. Kept because it was requested; reconsider if there is no strong reason for it.

---

## 3. Module Boundaries (inside the monolith)

```text
backend/app/
├── core/            config, db session, security primitives, money, errors, logging
├── identity/        users, product accounts, referrer enrollment, auth, API clients
├── catalog/         products, plans
├── referrals/       codes, clicks, attribution, referral relationships
├── events/          inbound event intake, signatures, idempotency, dispatch
├── subscriptions/   subscription and payment facts derived from events
├── commissions/     rules, resolution, calculation, lifecycle
├── ledger/          accounts, journal transactions, entries, balances
├── credits/         reservations, capture, release
├── payouts/         payout requests, methods, provider interface
├── campaigns/
├── partners/        partner types, agreements, tiers
├── risk/            signals, rules, scores, cases
├── notifications/   templates, channels, outbox dispatch
├── reporting/       read models, exports
└── admin/           admin-only endpoints, audit log
```

Rules:

- A module calls another module **only through its `service.py` public functions**, never its models or repositories.
- Only `ledger` writes ledger tables. Only `commissions` changes commission state.
- Cross-module reactions go through domain events (in-process bus + outbox), so a later split into services is mechanical.

---

## 4. System Invariants

Each one has an automated test (Section 22).

1. **I1 Balanced ledger.** Every journal transaction's entries sum to zero per currency.
2. **I2 Immutable history.** Ledger entries, journal transactions, audit logs and processed events are never updated or deleted. Corrections are new reversing entries.
3. **I3 Derivable balances.** Any account balance equals the sum of its ledger entries. Cached balances are reconciled nightly; a mismatch raises an alert.
4. **I4 Exactly-once effects.** One external event produces its business effects at most once, including under concurrent duplicate delivery.
5. **I5 No double spend.** Reservations, captures and payouts can never consume more than was available at the time of each operation.
6. **I6 One attribution.** A product account has at most one active referral attribution.
7. **I7 No self-referral.** A referrer never earns from their own product accounts.
8. **I8 Rule snapshot.** Every commission stores the exact rule version and inputs used. Recalculating from the snapshot gives the same amount.
9. **I9 No health data.** No medical or clinical data enters the platform. Inbound schemas reject unknown fields.

---

## 5. Identity and Authentication

### 5.1 Identity model

- `users`: a person who can log in to the platform (referrers, partners, admins).
- `product_accounts`: an account inside a connected product, unique on `(product_id, external_user_id)`. Linked to a `user_id` when that person is a referrer; otherwise unlinked (a referred customer who never logs in to the platform).
- **Never link product accounts to a user by matching email alone.** Links are created only through a verified handoff from that product (5.3) or by an admin, with an audit entry.

### 5.2 Referrer enrollment

- `POST /v1/referrers/enroll` (service): a product backend enrolls its logged-in user. The platform creates or finds the `user`, links the product account, creates wallet accounts and a referral code, and returns the code and portal link.
- Affiliates, agencies and resellers who are not product users sign up directly in the portal (email + OTP or password) and wait for admin approval if their partner type requires it.

### 5.3 Portal login

- **SSO handoff from a product:** product backend calls `POST /v1/auth/handoff` for the product account, gets a single-use token (60 s TTL), and redirects to `portal/auth/callback?token=…`. The portal exchanges it for a session.
- **Direct login** for non-product partners.
- Sessions: JWT access token (15 min, in memory) + rotating refresh token in an `HttpOnly`, `Secure`, `SameSite=Lax` cookie. Refresh-token reuse revokes the whole token family.

### 5.4 Roles

`SUPER_ADMIN`, `ADMIN`, `FINANCE_ADMIN`, `SUPPORT`, `RISK_ANALYST`, `PARTNER`, `CUSTOMER`. Endpoints check permissions via a central permission map, not role names scattered in code. Finance actions above a configurable amount need a second approver (maker-checker).

### 5.5 Service-to-service auth

- Each product has one or more `api_clients` with a key ID and secret. Store API secrets hashed and signing secrets encrypted.
- Requests carry `Authorization: Bearer <key_id>.<secret>`.
- **Two active secrets per client** for zero-downtime rotation.
- Scopes per client (`attribution:write`, `events:write`, `credits:write`, `referrers:enroll`, …). A client acts only for its own product; the product is taken from the credential, never from the request body.
- Service keys never reach a browser: browser → product backend → platform.

---

## 6. Referral Codes and Links

- Format: 4–16 chars from `A–Z` and `2–9` (excluding look-alikes `0 O 1 I L`). Stored uppercase; lookup is case-insensitive.
- Default code: readable prefix from the user's name + random suffix of at least 4 chars (e.g. `RAHIM7K3Q`). Vanity codes (`RAHIM82`) can be requested and need admin approval, with reserved-word and profanity checks.
- A user may hold several codes (e.g. per campaign). Codes can be deactivated, never reused.
- Canonical link: `https://ref.example.com/r/{CODE}` with optional `product`, `campaign`, `utm_*`. **Use `/r/` everywhere** (v1 mixed `/r/` and `/ref/`).
- `GET /v1/public/codes/{code}` returns only `valid` and the referrer's display name, rate-limited per IP against enumeration.

---

## 7. Attribution

### 7.1 Cross-domain click flow

A cookie on `ref.example.com` cannot be read by `healora.com`, so the click must travel with the user:

1. `GET /r/{CODE}?product=healora&campaign=OCT2026`
2. Platform validates the code, records a `referral_click` (hashed IP, user agent, UTM, campaign) and creates a signed **attribution token** (JWS) containing `click_id`, `code`, `product`, `campaign`, `iat`, `exp` (= attribution window).
3. Platform sets a first-party cookie on its own domain (for repeat visits) and redirects to the product's **registered** `signup_url` with `?ref=RAHIM82&rt=<token>`. Redirect targets come only from the product registry, never from the query string (no open redirect).
4. Product frontend stores `ref` and `rt`, pre-fills `<ReferralCodeInput />`, and sends both to its own backend on signup.
5. Product backend calls `POST /v1/attributions`.

If `product` is missing, show a small landing page listing the products the code works for.

### 7.2 Attribution request

```json
POST /v1/attributions
{
  "external_user_id": "HLR-456",
  "registered_at": "2026-10-08T14:58:00Z",
  "referral_code": "RAHIM82",
  "attribution_token": "eyJ...",
  "signals": { "ip": "103.x.x.x", "email": "k@x.com", "phone": "+8801...", "device_id": "..." }
}
```

### 7.3 Attribution rules (defaults configurable per product)

- **Scope:** per product account. Karim's Healora and PulsePOS accounts are attributed independently.
- **New accounts only:** accepted only if `registered_at` is within `attribution_grace_minutes` (default 60) of the call and the account has no prior paid events. Existing customers can only be attributed by an admin, with an audit entry.
- **Precedence:** a code typed or confirmed by the user at signup wins. The token supplies click and campaign linkage when its code matches. A valid token alone is enough.
- **Window:** token must be unexpired (7 / 30 / 60 / 90 days, per product or campaign).
- **First valid attribution wins and is locked.** Only an admin can change it (audited), and only before its first commission becomes AVAILABLE.
- **Self-referral is rejected** (same user, linked product account, or matching hashed email/phone).
- Idempotent on `(product_id, external_user_id)`: `201` new, `200` existing, or a standard error with a reason code. **Attribution failure must never block the product's signup**; the SDK fails soft.

### 7.4 Referral statuses

`ATTRIBUTED → TRIALING → CONVERTED → ACTIVE ⇄ INACTIVE`; terminal: `EXPIRED` (no conversion within window), `REJECTED` (risk), `REVOKED` (admin). Clicks live in their own table and are not a referral status.

---

## 8. Inbound Event Contract

### 8.1 Transport

Single endpoint `POST /v1/events` (replaces per-type URLs in v1). Headers:

```text
Authorization: Bearer <key_id>.<secret>
X-Signature-Timestamp: 1791470400
X-Signature: v1=<hex HMAC-SHA256(signing_secret, timestamp + "." + raw_body)>
```

- Reject timestamps more than 300 s from server time (replay protection). Constant-time comparison.
- On success, persist the raw event and return **`202 Accepted`** with the platform event ID. Processing is async.

### 8.2 Envelope

```json
{
  "event_id": "evt_01J…",
  "event_type": "payment.succeeded",
  "schema_version": 1,
  "occurred_at": "2026-10-08T15:00:00Z",
  "data": { }
}
```

### 8.3 Event types (v1)

| Type | Key `data` fields |
|---|---|
| `user.registered` | `external_user_id`, `registered_at`, `signals` |
| `subscription.created` / `.updated` | `subscription_id`, `external_user_id`, `plan_code`, `status`, `period_start`, `period_end` |
| `subscription.cancelled` / `.expired` | `subscription_id`, `effective_at` |
| `payment.succeeded` | `payment_id`, `subscription_id`, `external_user_id`, `plan_code`, `billing_reason` (`initial` / `renewal` / `upgrade` / `one_time`), `currency`, `amount_gross`, `discount_amount`, `tax_amount`, `credit_applied_amount`, `credit_reservation_id?`, `amount_net_paid`, `paid_at`, `payment_fingerprint?` |
| `payment.failed` | `payment_id`, `subscription_id`, `reason_code` |
| `payment.refunded` | `refund_id`, `payment_id`, `amount_refunded`, `currency`, `refunded_at` |
| `payment.chargeback` | `payment_id`, `amount`, `currency`, `opened_at` |

All money fields are integer minor units. All schemas use `extra="forbid"`.

### 8.4 Idempotency and ordering

- Unique on **`(product_id, event_id)`**. Event IDs are only unique within a product.
- Store SHA-256 of the canonical body. Same `event_id`, different body → `409 EVENT_ID_CONFLICT`.
- Business keys are also unique: `(product_id, payment_id)`, `(product_id, refund_id)`. This protects against a product resending the same payment under a new `event_id`.
- Events for one subscription are processed in order under a per-key advisory lock.
- An event whose dependency is missing (e.g. refund before payment) is parked as `WAITING_DEPENDENCY` and retried with backoff for up to 72 h, then dead-lettered with an admin alert.
- States: `RECEIVED → PROCESSING → PROCESSED | IGNORED (not referred / not eligible) | FAILED (retrying) | DEAD_LETTER`. Admins can replay dead letters; replay is idempotent.

### 8.5 Outbound webhooks (minimal in v1)

Products may register a URL to receive `credit.reservation_expired` and `referrer.code_changed`, signed the same way, with exponential-backoff retries and dead letter after 24 h.

---

## 9. Commission Engine

### 9.1 Rule model

`commission_rules` are **versioned**: editing creates a new version and closes the old one via `effective_until`. Fields:

- Scope (nullable = wildcard): `product_id`, `plan_id`, `partner_type`, `partner_id`, `campaign_id`, `billing_reason`, `level` (always 1 in v1).
- Calculation: `commission_type` (`PERCENTAGE` / `FIXED` / `TIERED`), `rate_bps` (1000 = 10%), `fixed_amount_minor`, `tier_schedule` (JSONB), `currency`.
- Limits: `min_net_paid_minor`, `max_commission_minor`, `eligible_months_from_conversion` (renewal window), `max_payments_per_referral`.
- Reward: `reward_split`, e.g. `{"WALLET": 100}` or `{"WALLET": 50, "CREDIT_ONLY": 50}` (credit-only funds can be spent as subscription credit but not withdrawn).
- Lifecycle: `confirmation_days`, `effective_from`, `effective_until`, `priority`, `status`.

### 9.2 Resolution (deterministic)

1. Load active rule versions with `effective_from <= paid_at < effective_until` whose non-null scope fields all match.
2. Rank by specificity: `partner_id` > `campaign_id` > `partner_type` > `plan_id` > `product_id` > global default; then `priority`.
3. A remaining tie is a configuration error: mark the payment `NEEDS_REVIEW` and alert. The admin UI must refuse to save rules that would tie.
4. Campaign rules apply only if the referral's click or attribution is linked to that campaign and the payment falls inside the campaign dates.

### 9.3 Calculation

- **Base = `amount_net_paid`** (gross − discount − tax − referral credit applied). No commission is ever paid on referral credit.
- `PERCENTAGE`: `base × rate_bps / 10000`, rounded once.
- `FIXED`: fixed amount, only if `base >= min_net_paid_minor`.
- `TIERED`: tier chosen by the referrer's count of **AVAILABLE conversions** in the tier period (`lifetime` / `calendar_month` / `rolling_30d`), evaluated at commission creation. Not retroactive by default.
- Apply `max_commission_minor`.
- Renewals: only with `billing_reason=renewal` and `paid_at` within `eligible_months_from_conversion` of conversion.
- Upgrades: commission on the net amount actually paid.
- A zero result creates no commission but logs the decision.
- Store `calculation_snapshot` JSONB: rule version, base, rate, tier, cap, rounding, inputs (I8).

### 9.4 Commission lifecycle

```text
PENDING ──(confirmation_days elapsed, no hold)──────────► AVAILABLE
   ├──(risk HIGH)──► ON_HOLD ──(cleared)──► PENDING / AVAILABLE
   │                         └─(rejected)──► REJECTED
   └──(full refund / payment failed)──────► CANCELLED
AVAILABLE ──(refund)──► REVERSED | PARTIALLY_REVERSED
```

- Commission state tracks **earning only**. Spending (credit use, withdrawal) lives in the ledger. (v1 mixed these with `WITHDRAWN` / `PARTIALLY_USED`.)
- An idempotent Beat job runs confirmation every 15 min.

---

## 10. Ledger and Wallet

### 10.1 Accounts

Per user, per currency (wallet unique on `(user_id, currency)`, not `user_id` alone):

| Account | Meaning |
|---|---|
| `user:pending` | earned, not yet confirmed |
| `user:available` | spendable and withdrawable |
| `user:credit_only` | spendable as subscription credit, not withdrawable |
| `user:reserved` | held by an open credit reservation |
| `user:payout_hold` | held by an open withdrawal request |

Platform accounts per currency: `platform:commission_expense`, `platform:credit_redeemed:{product}`, `platform:payout_clearing`, `platform:writeoff`.

### 10.2 Posting rules

| Business event | Debit | Credit |
|---|---|---|
| Commission created | `platform:commission_expense` | `user:pending` |
| Commission confirmed | `user:pending` | `user:available` / `user:credit_only` per split |
| Commission cancelled (pending) | `user:pending` | `platform:commission_expense` |
| Commission reversed (available) | `user:available` (or `credit_only`) | `platform:commission_expense` |
| Credit reserved | `user:available` / `user:credit_only` | `user:reserved` |
| Credit captured | `user:reserved` | `platform:credit_redeemed:{product}` |
| Credit released / expired | `user:reserved` | source account |
| Withdrawal requested | `user:available` | `user:payout_hold` |
| Withdrawal paid | `user:payout_hold` | `platform:payout_clearing` |
| Withdrawal rejected / failed | `user:payout_hold` | `user:available` |
| Manual adjustment / write-off | user account ↔ `platform:commission_expense` or `platform:writeoff` | |

Tables: `ledger_accounts`, `journal_transactions` (type, reference, `idempotency_key` UNIQUE, created_by), `ledger_entries` (account, signed amount, currency). Insert-only, enforced by a DB trigger rejecting `UPDATE`/`DELETE`.

### 10.3 Concurrency

- Every balance change runs in one DB transaction and locks the affected accounts with `SELECT … FOR UPDATE` in a fixed order (by account ID) to avoid deadlocks.
- An optional cached `ledger_account_balances` row is updated in the same transaction; the nightly job verifies it (I3).

### 10.4 Negative balances

A reversal after funds were spent can push `user:available` below zero. Default: allow it, block withdrawals while negative, net against future earnings, and let `FINANCE_ADMIN` write it off (audited). Configurable.

### 10.5 Portal balance names

**Pending**, **Available** (withdrawable), **Credit** (credit-only), **On hold** (reserved + payout hold), **Lifetime earned** (confirmed commissions − reversals).

---

## 11. Subscription Credit (two-phase)

A single "apply credit" call is unsafe: if the product's payment then fails, the credit is lost or applied twice. Use reserve → capture / release.

1. `GET /v1/credits/balance?external_user_id=…&currency=BDT` → spendable amount for the referrer linked to that product account.
2. `POST /v1/credits/reservations` `{external_user_id, currency, requested_amount, order_ref, idempotency_key}` → `{reservation_id, reserved_amount, expires_at}`. `reserved_amount = min(requested, spendable, per-invoice cap)`. TTL 15 min. Draws from `credit_only` first, then `available`.
3. Product charges `price − reserved_amount`.
4. On success, `payment.succeeded` carries `credit_reservation_id` and `credit_applied_amount`; the platform captures in the same transaction, or the product calls `POST /v1/credits/reservations/{id}/capture`.
5. On failure or abandonment, the product calls `/release`, or the expiry job releases it.

Rules: only product accounts linked to a referrer can spend credit; cross-product spending is allowed by default (per-product `accepts_cross_product_credit`); per-invoice cap configurable (default 100%); idempotent on `(product_id, idempotency_key)`.

---

## 12. Refunds, Chargebacks, Cancellations

- `payment.refunded` reverses commission proportionally: `round(commission × refunded / net_paid)`. Cumulative reversals never exceed the original commission.
- Commission `PENDING`: full refund → `CANCELLED`; partial → partial reversal, remainder stays pending.
- Commission `AVAILABLE`: reversal from the user's account (may go negative, 10.4).
- Chargeback: treated as refund plus a risk signal.
- Subscription cancellation stops future renewal commissions only.
- Refund of a payment that used referral credit: product calls `POST /v1/credits/refunds` to return the credit as a new posting referencing the original capture. Default: credit is returned.

---

## 13. Payouts

- Methods: `bkash`, `nagad`, `bank_transfer` (configurable). Main DB stores only masked identifiers; full details encrypted at rest with a separate key.
- Eligibility: verified email and phone; KYC `VERIFIED` where required (default for all partner types except CUSTOMER); available ≥ `min_payout`; no open HIGH risk case; balance not negative.
- Limits: `min_payout`, `max_payout_per_request`, `max_payouts_per_month`.
- States: `REQUESTED → UNDER_REVIEW → APPROVED → PROCESSING → PAID`, or `REJECTED` / `CANCELLED` / `FAILED` (funds return).
- Maker-checker above `dual_approval_threshold`: two different finance admins.
- Provider interface: `create(payout) -> provider_ref`, `get_status(ref)`, `handle_callback(payload)`. v1 ships `ManualPayoutProvider` (admin enters transfer reference, marks paid) and a CSV export for bulk bank uploads.
- Tax withholding hook per partner type, posted as a separate entry. Default 0% pending advice (Section 24).

---

## 14. Risk and Fraud

### 14.1 Signals

Products send raw `email`, `phone`, `ip`, `device_id`, `payment_fingerprint` over TLS. The platform **immediately HMACs them with a platform pepper and stores only hashes** (plus a hash of the IP /24 prefix). Raw values are never persisted or logged.

### 14.2 Rules (weighted, configurable)

Self-referral (hard block at attribution); referrer and referred sharing email, phone, device or payment fingerprint; many referrals from one subnet or device; conversion velocity above threshold; very short click → signup → payment time; high refund rate across a referrer's referrals; repeated minimum-payment-then-cancel patterns.

### 14.3 Outcomes

`LOW` / `MEDIUM` / `HIGH` / `BLOCKED`.

- `MEDIUM`: flag only.
- `HIGH`: new commissions for that referral or referrer go `ON_HOLD`; a `risk_case` opens.
- `BLOCKED`: set only by a human analyst; blocks new attributions and payouts.

Nothing permanent happens automatically. Cases have an assignee, notes, evidence (hash matches), and an audited decision.

---

## 15. Privacy and Healthcare Data

- The platform needs only product account IDs, plans, payment amounts and dates, and hashed risk signals. `extra="forbid"` schemas reject anything else.
- Even the fact that someone uses Healora can be sensitive. Per-product `referrer_visibility`: `NONE` (counts only), `MASKED` (default: "K\*\*\*\*m · Healora"), `FULL` (only with the referred user's consent flag from the product).
- Erasure requests pseudonymize PII on `users` and `product_accounts`; ledger and audit rows are kept with pseudonymous references.
- Logs never contain passwords, tokens, secrets, raw signals, payout details or health data. A logging filter enforces this and is unit-tested.
- Retention configurable (defaults: clicks 13 months, raw event payloads 24 months, ledger and audit indefinite).

---

## 16. Notifications

- Channels: in-app and email (SMTP) in v1; push via provider interface (stub).
- Triggers: referral attributed, commission earned / available / reversed, credit applied, withdrawal approved / rejected / paid, campaign started.
- Templates per event, channel and locale (`en`, `bn`), admin-editable, versioned, rendered with Jinja2 `SandboxedEnvironment`.
- Users can opt out per category, except transactional finance notices.
- All sends go through the outbox with delivery status tracked.

---

## 17. Admin Panel and Audit

### 17.1 Sections

Dashboard · Users & Partners (approval queue) · Products & Plans (signup URL allowlist, refund window, visibility, credit acceptance) · API Clients (create, rotate, revoke) · Referral Codes · Campaigns · Commission Rules (versioned editor + **rule simulator**: enter product, plan, partner, amount → see winning rule and result) · Referrals · Commissions · Wallets & Ledger (read-only journal viewer) · Credit Reservations · Payouts (review, maker-checker) · Risk Cases · Events (search, inspect, replay dead letters) · Notifications & Templates · Reports · Audit Log · Settings.

### 17.2 Dashboard

Referrers, referrals, conversion rate, referred revenue (net paid), commission pending / available / paid, credit redeemed by product, payouts, open risk cases, dead-letter count. Charts: daily referrals, monthly referred revenue vs commission cost, conversion rate, product comparison, top referrers, campaign performance. Filters: date, product, partner type, campaign.

### 17.3 Reports

Referral, commission, revenue, partner, campaign, payout, risk, product performance. Filters as above; CSV export. Report totals must reconcile with the ledger.

### 17.4 Audit log

Every admin write records actor, action, entity, before/after diff, IP, request ID, time. Insert-only (DB trigger). No edit or delete in any UI. Exportable.

---

## 18. Customer Portal (React)

- Pages: Dashboard (code, copy link, per-product links, QR, share), Referrals (masked table), Earnings, Wallet (ledger-backed history), Withdrawals, Settings (profile, notifications, payout methods, KYC upload).
- Charts: referrals over time, conversions, earnings, product breakdown.
- **Theming:** the portal loads a per-product theme from `GET /v1/public/products/{code}/theme`, so a user arriving from Healora sees Healora branding. This is how the v1 requirement "feel like part of the existing product" is met.
- Embeddable package `@platform/referral-ui`: `<ReferralCodeInput />` (validates via the product's own backend, never a service key), `<ReferralSummaryCard />`.
- WCAG 2.1 AA, mobile-first, i18n `en` and `bn`.

---

## 19. SDKs and Integration Kit

### 19.1 Python SDK (`sdk/python/referral_client`)

`client.py`, `models.py` (Pydantic, generated from OpenAPI where practical), `exceptions.py`, `webhook.py` (sign/verify), `events.py` (typed event builders). Async and sync clients. Retries with backoff for 5xx/network errors only. Auto-generated idempotency keys. Fail-soft helpers for signup paths.

```python
client = ReferralClient(base_url=settings.REFERRAL_URL, key_id=..., secret=..., signing_secret=...)

await client.attribute(
    external_user_id=user.id, registered_at=user.created_at,
    referral_code=form.referral_code, attribution_token=form.rt,
    signals=Signals(ip=request.client.host, email=user.email),
)
await client.send_event(PaymentSucceeded(...))
res = await client.reserve_credit(external_user_id=user.id, currency="BDT",
                                  requested_amount=100_000, order_ref=order.id)
```

### 19.2 TypeScript

- `sdk/typescript/server`: the same client for Node backends.
- `sdk/typescript/browser`: only helpers to read and persist `ref` / `rt`. **No credentials.**

### 19.3 Product simulator

`tools/product-simulator`: a small FastAPI app acting as a connected product (signup reading `rt`, fake checkout with credit, signed events, refunds, duplicate and out-of-order sending). Used by integration tests and demos.

### 19.4 Integration docs

`docs/integration.md` (generic contract and checklist), `docs/pulsepos-integration.md`, `docs/healora-integration.md` (with privacy rules): sequence diagram, required events, sample code, test checklist, go-live checklist.

---

## 20. API Surface (v1)

All under `/v1` (gateway may expose as `/api/v1`).

| Group | Endpoints |
|---|---|
| Public | `GET /r/{code}`, `GET /public/codes/{code}`, `GET /public/products/{code}/theme` |
| Auth | `POST /auth/login`, `/auth/otp/*`, `/auth/refresh`, `/auth/logout`, `/auth/handoff` (service), `/auth/handoff/exchange` |
| Service | `POST /referrers/enroll`, `POST /attributions`, `GET /attributions/{external_user_id}`, `POST /events`, `GET /credits/balance`, `POST /credits/reservations`, `POST /credits/reservations/{id}/capture`, `POST /credits/reservations/{id}/release`, `POST /credits/refunds` |
| Me | `GET /me`, `GET/POST /me/codes`, `GET /me/referrals`, `GET /me/commissions`, `GET /me/wallet`, `GET /me/wallet/transactions`, `GET/POST /me/payout-methods`, `GET/POST /me/payouts`, `GET /me/analytics`, `GET /me/notifications` |
| Admin | `/admin/{users,partners,products,plans,api-clients,codes,campaigns,commission-rules,commission-rules/simulate,referrals,commissions,wallets,ledger,reservations,payouts,risk-cases,events,events/{id}/replay,templates,reports,audit-logs,settings}` |
| Ops | `GET /health`, `GET /ready` (DB, Redis, migrations at head), `GET /metrics` |

Conventions:

- Cursor pagination (`?cursor=&limit=`, max 100).
- `Idempotency-Key` header required on all non-event POSTs that move money.
- Errors:

```json
{ "success": false, "error": { "code": "REFERRAL_CODE_INVALID", "message": "…", "request_id": "…", "details": {} } }
```

- Central error-code registry in `docs/api.md`.
- `/openapi.json`, Swagger at `/docs`, ReDoc at `/redoc`; disabled or auth-protected in production. Every endpoint documents auth, schemas, errors and examples.

---

## 21. Data Model

Tables (UUIDv7 PK, `created_at`, `updated_at`; `*` = soft delete allowed):

`users`*, `user_roles`, `refresh_tokens`, `api_clients`, `api_client_secrets`, `products`*, `plans`*, `product_accounts`, `partners`, `partner_types`, `referral_codes`, `referral_clicks`, `referrals`, `campaigns`*, `commission_rules` (versioned), `subscriptions`, `payments`, `refunds`, `commissions`, `commission_reversals`, `ledger_accounts`, `ledger_account_balances`, `journal_transactions`, `ledger_entries`, `credit_reservations`, `payout_methods`, `payouts`, `payout_approvals`, `inbound_events`, `outbox`, `outbound_webhooks`, `risk_signals`, `risk_cases`, `notification_templates`, `notifications`, `audit_logs`, `settings` (versioned).

Financial, event and audit tables are never soft-deleted.

Key constraints:

- `referral_codes(code)` UNIQUE
- `product_accounts(product_id, external_user_id)` UNIQUE
- `referrals(referred_product_account_id)` partial UNIQUE where status is active (I6)
- `inbound_events(product_id, event_id)` UNIQUE
- `payments(product_id, payment_id)` UNIQUE; `refunds(product_id, refund_id)` UNIQUE
- `commissions(payment_id, referral_id, level)` UNIQUE
- `journal_transactions(idempotency_key)` UNIQUE
- `ledger_accounts(owner_type, owner_id, kind, currency)` UNIQUE
- `credit_reservations(product_id, idempotency_key)` UNIQUE
- CHECK constraints on amounts, currency codes and state enums

Multi-level readiness: `referrals.parent_referral_id`, `commissions.level`, feature flag `multi_level.enabled=false`. No v1 code path reads level > 1.

Deliver the ERD as Mermaid in `docs/erd.md` in Phase 0.

---

## 22. Quality Requirements

### 22.1 Non-functional targets

| Item | Target |
|---|---|
| `POST /attributions` | p95 < 300 ms |
| `POST /events` acknowledgement | p95 < 200 ms |
| Portal read APIs | p95 < 250 ms |
| Event processing lag | p95 < 30 s |
| Availability | 99.9% monthly |
| Backups | PostgreSQL PITR, RPO ≤ 5 min, RTO ≤ 1 h, monthly restore drill |
| Baseline scale | 100 events/s sustained, 1M product accounts |

Rate limits per API client and per IP on public endpoints (Redis token bucket).

### 22.2 Observability

Structured JSON logs with `request_id`, `api_client_id`, `user_id`, `product_id`, `event_id`, `operation`, `status`, `duration_ms`. OpenTelemetry traces API → task. Prometheus metrics: events by state, dead letters, commission totals, reconciliation result, queue depth. Sentry-compatible error hook. Alerts: dead letters > 0, reconciliation mismatch, rule tie, payout failures.

### 22.3 Security

OWASP ASVS Level 2 as checklist. Secrets from environment or a secret manager. CORS limited to portal and admin origins. CSP on frontends. Dependency scanning in CI. Admin on a separate hostname, optional IP allowlist, TOTP 2FA required for admin roles. No stack traces in production responses.

### 22.4 Tests (all run in CI)

- **Unit:** codes, attribution rules, rule resolution (every specificity case, tie detection), calculation (percentage, fixed, tiered, caps, rounding edges), lifecycle transitions, posting rules, refund proration, risk rules, log redaction.
- **Property-based (Hypothesis):** I1, I3, and random sequences of earn / confirm / reserve / capture / release / refund / withdraw never violating I5.
- **Concurrency:** 20 parallel deliveries of one event → one commission; 20 parallel reservations against one balance → total ≤ available.
- **Integration** (simulator + real Postgres/Redis via testcontainers): acceptance scenario; refund before and after confirmation; refund after withdrawal; out-of-order refund; renewal inside and outside window; campaign override; reserve → payment fail → release.
- **Security:** missing / invalid / revoked key, cross-product access, bad signature, stale-timestamp replay, expired JWT, refresh-token reuse, self-referral, code enumeration, open-redirect attempt.
- **Contract:** SDKs against the OpenAPI schema.
- **Coverage:** ≥ 95% lines and branches on `commissions`, `ledger`, `credits`, `payouts`, `events`; ≥ 80% overall.

---

## 23. Delivery Phases

Each phase ends with a phase report and passing exit criteria.

| # | Phase | Scope | Exit criteria |
|---|---|---|---|
| 0 | Design | ADRs, ERD, OpenAPI draft, event JSON Schemas, sequence diagrams for the acceptance scenario, threat model | Docs reviewed; no contradictions left |
| 1 | Foundation | Repo layout, Compose (Postgres, Redis, API, worker, beat, Nginx), config, logging, errors, health/ready, Alembic, CI, money and time utilities | `docker compose up` healthy; CI green |
| 2 | Identity & catalog | Users, roles, JWT + refresh, API clients with scopes and rotation, products, plans, product accounts, enrollment, SSO handoff | Auth security tests pass |
| 3 | Referrals | Codes, `/r/` redirect + click + token, `POST /attributions` with all 7.3 rules, self-referral block | Attribution unit + security tests pass |
| 4 | Events | `/v1/events`, signatures, idempotency, ordering, dependency parking, dead letter, replay, outbox | Duplicate and out-of-order tests pass |
| 5 | Commission + ledger | Versioned rules, resolution, calculation, lifecycle, confirmation job, accounts and posting rules, reconciliation job | **Acceptance scenario passes end-to-end with the simulator**; property tests pass |
| 6 | Refunds & renewals | Proportional reversal, chargebacks, negative balance policy, renewal windows, upgrades | Refund and renewal integration tests pass |
| 7 | Credits | Reserve / capture / release / expire / credit refund | Double-spend concurrency tests pass |
| 8 | SDKs & docs | Python + TS SDKs, simulator, PulsePOS and Healora integration guides | A new developer integrates the simulator using only the docs |
| 9 | Customer portal | React portal, theming, embeddable components | Playwright E2E: login, dashboard, referrals, wallet |
| 10 | Admin panel | Quasar admin incl. rule simulator, events console, audit log | E2E: rule edit → audit entry; event replay |
| 11 | Payouts | Methods, requests, review, maker-checker, manual provider, CSV export | Payout state and ledger tests pass |
| 12 | Risk | Signal hashing, rules, scoring, holds, cases, review workflow | Holds block confirmation; risk tests pass |
| 13 | Notifications & reports | Email + in-app, templates (en/bn), reports with CSV | Report totals reconcile with ledger |
| 14 | Hardening | Load test against 22.1, ASVS review, backup/restore drill, prod Compose, runbooks | Targets met; runbooks in `docs/runbooks/` |

**MVP = Phases 0–8**: the smallest system that runs the acceptance scenario with correct money semantics. Real product integrations (PulsePOS first, then Healora, then System 3/4) start after Phase 8, in parallel with Phases 9+.

---

## 24. Open Business Questions (with defaults)

| # | Question | Default until decided |
|---|---|---|
| Q1 | Commission base: gross, net of discount, net of tax? | Net cash paid, excluding tax and referral credit |
| Q2 | Confirmation period per product? | 14 days, or the product's refund window if longer |
| Q3 | Can credit earned on one product be spent on another? | Yes |
| Q4 | Does referral credit expire? | No |
| Q5 | Reversal larger than available balance? | Negative balance, netted against future earnings |
| Q6 | Can an existing customer of one product be referred into another? | Yes, per product account |
| Q7 | Typed code vs clicked link conflict? | Typed code wins |
| Q8 | Payout methods and KYC? | bKash, Nagad, bank; KYC for non-CUSTOMER partners |
| Q9 | Tax withholding on payouts? | 0%, configurable; confirm with a tax advisor |
| Q10 | Who bears the cost when credit from product A is spent on product B? | Recorded per product; settled outside the platform |
| Q11 | Multi-level commissions? | Disabled; legal review required before enabling |
| Q12 | What referrers may see about referred users, per product? | MASKED; NONE for Healora if legal advises |
| Q13 | Currencies? | BDT only in v1; schema supports more |
| Q14 | Default rates? | 10% first payment, 5% renewals for 12 months |
| Q15 | Is the referral code field ever mandatory? | Optional; per-product setting |

---

## 25. Repository Layout

```text
referral-platform/
├── backend/                app/ (modules per Section 3), tests/, alembic/, Dockerfile, pyproject.toml
├── portal/                 React customer portal + packages/referral-ui
├── admin/                  Quasar admin
├── sdk/python/             referral_client
├── sdk/typescript/         server/, browser/
├── tools/product-simulator/
├── deploy/                 nginx/, backup scripts
├── docs/                   architecture.md, erd.md, api.md, events.md, integration.md,
│                           pulsepos-integration.md, healora-integration.md, deployment.md,
│                           runbooks/, adr/
├── docker-compose.yml, docker-compose.dev.yml, docker-compose.prod.yml
├── .env.example            every variable documented, no real secrets
└── README.md               5-minute local quickstart
```

`.env.example` includes at least: `APP_ENV`, `DATABASE_URL`, `REDIS_URL`, `JWT_SIGNING_KEY`, `ATTRIBUTION_TOKEN_KEY`, `SIGNAL_HASH_PEPPER`, `PAYOUT_DETAILS_ENCRYPTION_KEY`, `SECRETS_ENCRYPTION_KEY`, `REFERRAL_BASE_URL`, `PORTAL_URL`, `ADMIN_URL`, `SMTP_*`, `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT`.

Product API keys are **not** environment variables. They are created per product in the admin panel (or a seed CLI for local dev) and stored hashed, so adding Product 5 needs no redeploy.
