# Entity-Relationship Model

Source of truth for table design (Phase 0 deliverable, §21). Split by module because one
diagram of ~50 tables is unreadable. Conventions:

- Every PK is `id uuid` (UUIDv7, ADR 0003). Omitted from diagrams where obvious.
- Mutable tables have `created_at`, `updated_at` (`timestamptz`, UTC). Insert-only tables
  (ADR 0006, marked **[IO]**) have `created_at` only and a `forbid_mutation` trigger.
- Soft delete (`deleted_at`) only where §21 allows: `users`, `products`, `plans`,
  `campaigns`. Marked **[SD]**.
- Money: `*_minor bigint` + `currency char(3)`. CHECK `currency ~ '^[A-Z]{3}$'`.
- Enums are `text` + CHECK constraint (easier migrations than PG enums).
- Tables added beyond §21 are marked **(+ADR nnnn)** or **(+)** with a reason in §Additions.

## 1. Identity, catalog, partners

```mermaid
erDiagram
    users ||--o{ user_roles : has
    users ||--o{ refresh_tokens : has
    users ||--o{ product_accounts : "linked (optional)"
    users ||--o| partners : "is (optional)"
    users ||--o{ kyc_submissions : submits
    partner_types ||--o{ partners : classifies
    products ||--o{ plans : offers
    products ||--o{ api_clients : "authenticates as"
    api_clients ||--o{ api_client_secrets : "has (max 2 active)"
    products ||--o{ product_accounts : contains
    products ||--o{ auth_handoff_tokens : issues
    product_accounts ||--o{ auth_handoff_tokens : for

    users {
        uuid id PK
        text email "nullable, unique ci where not null"
        bool email_verified
        text phone "E.164, nullable"
        bool phone_verified
        text password_hash "argon2id, nullable"
        text display_name
        text locale "en|bn"
        text time_zone "default Asia/Dhaka"
        text status "ACTIVE|SUSPENDED|PSEUDONYMIZED"
        text kyc_status "NONE|PENDING|VERIFIED|REJECTED"
        text totp_secret_enc "admins, encrypted"
        timestamptz deleted_at "SD"
    }
    user_roles {
        uuid user_id FK
        text role "SUPER_ADMIN|ADMIN|FINANCE_ADMIN|SUPPORT|RISK_ANALYST|PARTNER|CUSTOMER"
        uuid granted_by FK
    }
    refresh_tokens {
        uuid user_id FK
        uuid family_id
        bytea token_hash UK
        uuid replaced_by FK "rotation chain"
        timestamptz expires_at
        timestamptz revoked_at
        text revoke_reason "LOGOUT|ROTATED|REUSE_DETECTED|ADMIN"
    }
    auth_handoff_tokens {
        bytea token_hash UK
        uuid product_id FK
        uuid product_account_id FK
        timestamptz expires_at "60 s"
        timestamptz consumed_at "single use"
    }
    otp_challenges {
        text channel "EMAIL|SMS"
        text destination_hash
        text code_hash
        int attempts
        timestamptz expires_at
        timestamptz consumed_at
    }
    products {
        text slug UK "ADR 0019"
        text name
        text status "ACTIVE|DISABLED"
        text signup_url "registered redirect target"
        text_arr allowed_redirect_hosts
        int attribution_window_days "7|30|60|90"
        int attribution_grace_minutes "ADR 0013, default 1440"
        int conversion_window_days "ADR 0014, default 90"
        int refund_window_days
        int confirmation_days "Q2"
        text referrer_visibility "NONE|MASKED|FULL"
        bool sensitive_category "ADR 0016"
        bool accepts_cross_product_credit
        int credit_max_invoice_pct "default 100"
        bool referral_code_required "Q15"
        jsonb theme "portal theming"
        text outbound_webhook_url
        bytea outbound_signing_secret_enc
        timestamptz deleted_at "SD"
    }
    plans {
        uuid product_id FK
        text plan_code "UK with product_id"
        text name
        text status
        timestamptz deleted_at "SD"
    }
    api_clients {
        uuid product_id FK
        text name
        text key_id UK
        text_arr scopes
        text status "ACTIVE|REVOKED"
    }
    api_client_secrets {
        uuid api_client_id FK
        bytea secret_hash "argon2id/sha256+pepper"
        bytea signing_secret_enc "AES-GCM, SECRETS_ENCRYPTION_KEY"
        text status "ACTIVE|RETIRED"
        timestamptz expires_at
    }
    product_accounts {
        uuid product_id FK
        text external_user_id "UK with product_id"
        uuid user_id FK "nullable; set only via handoff/admin"
        timestamptz registered_at
        bool visibility_consent "for FULL"
        text display_name_masked
        timestamptz first_paid_at
    }
    partner_types {
        text code UK "CUSTOMER|AFFILIATE|AGENCY|RESELLER|..."
        bool requires_approval
        bool requires_kyc
        int tax_withholding_bps "default 0, Q9"
    }
    partners {
        uuid user_id FK "UK"
        uuid partner_type_id FK
        text status "PENDING_APPROVAL|ACTIVE|SUSPENDED|REJECTED"
        uuid approved_by FK
        jsonb agreement "terms version accepted"
    }
    kyc_submissions {
        uuid user_id FK
        text status "PENDING|VERIFIED|REJECTED"
        text document_type
        text storage_ref "encrypted object store key"
        uuid reviewed_by FK
    }
```

## 2. Referrals and campaigns

```mermaid
erDiagram
    users ||--o{ referral_codes : owns
    campaigns ||--o{ referral_codes : "scoped (optional)"
    referral_codes ||--o{ referral_clicks : receives
    referral_codes ||--o{ referrals : "attributed via"
    referral_clicks ||--o| referrals : "linked (optional)"
    product_accounts ||--o{ referrals : "is referred (max 1 active)"
    referrals ||--o| referrals : "parent (multi-level, disabled)"
    campaigns ||--o{ referrals : "linked (optional)"

    referral_codes {
        text code UK "uppercase, A-Z 2-9 minus look-alikes"
        uuid user_id FK
        uuid campaign_id FK "nullable"
        text kind "DEFAULT|VANITY"
        text status "PENDING_APPROVAL|ACTIVE|DEACTIVATED|REJECTED"
        uuid approved_by FK
    }
    referral_clicks {
        uuid referral_code_id FK
        uuid product_id FK "nullable: landing page"
        uuid campaign_id FK
        bytea ip_hash "HMAC pepper"
        bytea ip_prefix_hash "/24"
        text user_agent
        jsonb utm
        timestamptz clicked_at
    }
    campaigns {
        text slug UK
        text name
        uuid product_id FK "nullable = all"
        timestamptz starts_at
        timestamptz ends_at
        int attribution_window_days "override"
        text status
        timestamptz deleted_at "SD"
    }
    referrals {
        uuid referrer_user_id FK
        uuid referral_code_id FK
        uuid referred_product_account_id FK
        uuid click_id FK
        uuid campaign_id FK
        text source "TYPED_CODE|TOKEN|TYPED_AND_TOKEN|ADMIN"
        text status "ATTRIBUTED|TRIALING|CONVERTED|ACTIVE|INACTIVE|EXPIRED|REJECTED|REVOKED"
        timestamptz attributed_at
        timestamptz converted_at
        uuid parent_referral_id FK "multi-level, always null in v1"
        int level "always 1"
        bool locked "true after first commission AVAILABLE"
    }
```

## 3. Events, subscriptions, payments

```mermaid
erDiagram
    api_clients ||--o{ inbound_events : sent
    inbound_events ||--|| inbound_event_payloads : "raw body (purgeable)"
    inbound_events ||--|| event_processing : "state"
    event_processing ||--o{ event_processing_log : history
    product_accounts ||--o{ subscriptions : has
    subscriptions ||--o{ payments : bills
    product_accounts ||--o{ payments : pays
    payments ||--o{ refunds : refunded
    payments ||--o{ chargebacks : disputed
    credit_reservations |o--o| payments : "used by"

    inbound_events {
        uuid product_id FK "IO"
        text event_id "UK with product_id"
        text event_type
        int schema_version
        timestamptz occurred_at
        bytea body_sha256
        uuid api_client_id FK
        timestamptz received_at
        text ordering_key "ADR 0012"
    }
    inbound_event_payloads {
        uuid inbound_event_id PK "FK"
        jsonb body "deleted by retention job only"
    }
    event_processing {
        uuid inbound_event_id PK "FK"
        text state "RECEIVED|PROCESSING|PROCESSED|IGNORED|FAILED|WAITING_DEPENDENCY|DEAD_LETTER"
        int attempts
        timestamptz next_attempt_at
        text outcome_code "e.g. NOT_REFERRED, REFERRAL_EXPIRED"
        text last_error_code
        text last_error
        timestamptz processed_at
    }
    event_processing_log {
        uuid inbound_event_id FK "IO"
        text from_state
        text to_state
        text detail
        uuid actor_id "replay by admin"
    }
    subscriptions {
        uuid product_id FK
        text subscription_id "UK with product_id"
        uuid product_account_id FK
        uuid plan_id FK
        text status
        timestamptz period_start
        timestamptz period_end
        timestamptz cancelled_at
    }
    payments {
        uuid product_id FK
        text payment_id "UK with product_id"
        uuid product_account_id FK
        uuid subscription_id FK "nullable (one_time)"
        uuid plan_id FK
        text billing_reason "initial|renewal|upgrade|one_time"
        char3 currency
        bigint amount_gross_minor
        bigint discount_minor
        bigint tax_minor
        bigint credit_applied_minor
        bigint amount_net_paid_minor "CHECK = gross-discount-tax-credit"
        uuid credit_reservation_id FK
        text status "SUCCEEDED|FAILED|REFUNDED|PARTIALLY_REFUNDED"
        timestamptz paid_at
        bytea payment_fingerprint_hash
        uuid source_event_id FK
    }
    refunds {
        uuid product_id FK
        text refund_id "UK with product_id"
        uuid payment_id FK
        bigint amount_minor
        char3 currency
        timestamptz refunded_at
        uuid source_event_id FK
    }
    chargebacks {
        uuid product_id FK
        text chargeback_id "UK with product_id, ADR 0010"
        uuid payment_id FK
        bigint amount_minor
        char3 currency
        text outcome "OPEN|WON|LOST"
        timestamptz opened_at
        timestamptz resolved_at
    }
```

## 4. Commissions and ledger

```mermaid
erDiagram
    commission_rules ||--o{ commissions : "version used"
    payments ||--o{ commissions : generates
    referrals ||--o{ commissions : earns
    commissions ||--o{ commission_reversals : reversed
    commissions ||--o{ commission_state_transitions : history
    ledger_accounts ||--o{ ledger_entries : posted
    journal_transactions ||--|{ ledger_entries : "balanced set"
    ledger_accounts ||--o| ledger_account_balances : cache
    ledger_adjustments ||--o| journal_transactions : posts

    commission_rules {
        uuid rule_id "stable across versions"
        int version "UK with rule_id"
        uuid product_id FK "null = wildcard"
        uuid plan_id FK
        text partner_type
        uuid partner_id FK
        uuid campaign_id FK
        text billing_reason
        int level "always 1"
        text commission_type "PERCENTAGE|FIXED|TIERED"
        int rate_bps
        bigint fixed_amount_minor
        jsonb tier_schedule
        char3 currency
        bigint min_net_paid_minor
        bigint max_commission_minor
        int eligible_months_from_conversion
        int max_payments_per_referral
        jsonb reward_split "WALLET/CREDIT_ONLY sums to 100"
        int confirmation_days "null = product default"
        timestamptz effective_from
        timestamptz effective_until "null = open"
        int priority
        text status "DRAFT|ACTIVE|CLOSED"
        bytea scope_fingerprint "tie detection"
    }
    commissions {
        uuid payment_id FK
        uuid referral_id FK
        int level "UK (payment_id, referral_id, level)"
        uuid referrer_user_id FK
        uuid commission_rule_id FK
        int commission_rule_version
        char3 currency
        bigint amount_minor "immutable"
        bigint reversed_minor "cumulative"
        text state "PENDING|ON_HOLD|AVAILABLE|PARTIALLY_REVERSED|REVERSED|CANCELLED|REJECTED"
        timestamptz eligible_at
        timestamptz confirmed_at
        jsonb reward_split_applied
        jsonb calculation_snapshot "I8"
    }
    commission_reversals {
        uuid commission_id FK "IO"
        text source_ref "refund:/chargeback:/payment-failed:/admin:"
        bigint amount_minor
        jsonb calculation_snapshot "ADR 0009"
        uuid journal_transaction_id FK
    }
    commission_state_transitions {
        uuid commission_id FK "IO"
        text from_state
        text to_state
        text reason
        uuid actor_id
    }
    ledger_accounts {
        text owner_type "USER|PLATFORM"
        uuid owner_id "user id, or product id for credit_redeemed"
        text kind "pending|available|credit_only|reserved|payout_hold|commission_expense|credit_redeemed|payout_clearing|tax_withholding_payable|writeoff"
        char3 currency
        text normal_side "DEBIT|CREDIT"
    }
    journal_transactions {
        text type "P1..P16 name"
        text reference_type
        uuid reference_id
        text idempotency_key UK
        uuid created_by
        timestamptz created_at "IO"
    }
    ledger_entries {
        uuid journal_transaction_id FK "IO"
        uuid ledger_account_id FK
        bigint amount_minor "signed: + debit, - credit"
        char3 currency
    }
    ledger_account_balances {
        uuid ledger_account_id PK "FK"
        bigint balance_minor "SUM(entries)"
        uuid last_entry_id
    }
    ledger_adjustments {
        text kind "WRITEOFF|BONUS|CLAWBACK"
        uuid user_id FK
        bigint amount_minor
        char3 currency
        text reason
        uuid requested_by FK
        uuid approval_id FK
        text status "PENDING_APPROVAL|POSTED|REJECTED"
    }
```

## 5. Credits and payouts

```mermaid
erDiagram
    users ||--o{ credit_reservations : "spends via"
    products ||--o{ credit_reservations : "redeemed at"
    product_accounts ||--o{ credit_reservations : "requested for"
    credit_reservations ||--o{ credit_refunds : returned
    users ||--o{ payout_methods : has
    users ||--o{ payouts : requests
    payout_methods ||--o{ payouts : "paid to"
    payouts ||--o{ approvals : "maker-checker"
    ledger_adjustments ||--o{ approvals : "maker-checker"

    credit_reservations {
        uuid product_id FK
        text idempotency_key "UK with product_id"
        uuid product_account_id FK
        uuid user_id FK
        text order_ref
        char3 currency
        bigint requested_minor
        bigint reserved_minor
        bigint from_credit_only_minor
        bigint from_available_minor
        bigint captured_minor
        bigint late_captured_minor "ADR 0011"
        text payment_id
        text state "RESERVED|CAPTURED|PARTIALLY_CAPTURED|RELEASED|EXPIRED|LATE_CAPTURED"
        timestamptz expires_at
    }
    credit_refunds {
        uuid product_id FK
        text idempotency_key "UK with product_id"
        uuid credit_reservation_id FK
        bigint amount_minor "cum <= captured"
        uuid journal_transaction_id FK
    }
    payout_methods {
        uuid user_id FK
        text method "bkash|nagad|bank_transfer"
        text masked_identifier "e.g. 01*******89"
        bytea details_enc "PAYOUT_DETAILS_ENCRYPTION_KEY"
        text status "ACTIVE|DISABLED"
        timestamptz verified_at
    }
    payouts {
        uuid user_id FK
        uuid payout_method_id FK
        char3 currency
        bigint amount_minor "gross"
        bigint tax_withheld_minor
        bigint net_minor
        text state "REQUESTED|UNDER_REVIEW|APPROVED|PROCESSING|PAID|REJECTED|CANCELLED|FAILED|RETURNED"
        text provider "manual"
        text provider_ref
        text idempotency_key UK
        bool needs_review "ADR 0008"
    }
    approvals {
        text entity_type "payout|ledger_adjustment|rule_activation"
        uuid entity_id
        uuid requested_by FK
        uuid approved_by FK "must differ from requested_by"
        text decision "APPROVED|REJECTED"
        text note
    }
```

## 6. Risk, notifications, audit, settings, integration

```mermaid
erDiagram
    users ||--o{ risk_signals : "about (optional)"
    product_accounts ||--o{ risk_signals : "about (optional)"
    risk_cases ||--o{ risk_signals : evidence
    users ||--o{ notifications : receives
    notification_templates ||--o{ notifications : renders
    products ||--o{ reconciliation_runs : submits

    risk_signals {
        text kind "EMAIL|PHONE|IP|IP_PREFIX|DEVICE|PAYMENT_FP|CHARGEBACK|..."
        bytea value_hash "HMAC(pepper, normalized value)"
        uuid product_account_id FK
        uuid user_id FK
        uuid source_event_id FK
        timestamptz created_at "IO"
    }
    risk_cases {
        uuid subject_user_id FK
        uuid referral_id FK
        text level "MEDIUM|HIGH|BLOCKED"
        int score
        jsonb reasons
        text status "OPEN|CLEARED|REJECTED|BLOCKED"
        uuid assignee_id FK
        jsonb notes
        uuid decided_by FK
    }
    notification_templates {
        text event_key
        text channel "IN_APP|EMAIL|PUSH"
        text locale "en|bn"
        int version
        text subject
        text body "Jinja2 sandboxed"
        bool active
    }
    notifications {
        uuid user_id FK
        text category
        text channel
        uuid template_id FK
        jsonb context
        text status "QUEUED|SENT|FAILED|READ"
        timestamptz read_at
    }
    outbox {
        text topic "notification|webhook|task"
        jsonb payload
        text dedupe_key UK
        text status "PENDING|DISPATCHED|FAILED|DEAD"
        int attempts
        timestamptz next_attempt_at
    }
    outbound_webhook_deliveries {
        uuid product_id FK
        text event_type
        jsonb payload
        int attempts
        int last_status_code
        text status "PENDING|DELIVERED|DEAD"
    }
    audit_logs {
        uuid actor_id "IO"
        text actor_type "USER|CLI|SYSTEM|API_CLIENT"
        text action
        text entity_type
        uuid entity_id
        jsonb before
        jsonb after
        inet ip
        text request_id
    }
    settings {
        text key
        int version "UK (key, version)"
        jsonb value
        uuid changed_by
        bool active
    }
    reconciliation_runs {
        uuid product_id FK
        date business_date
        int submitted_count
        int missing_count
        int mismatch_count
        jsonb details
    }
```

## Key constraints

From §21, plus additions:

| Constraint | Purpose |
|---|---|
| `referral_codes(code)` UNIQUE | codes never reused |
| `product_accounts(product_id, external_user_id)` UNIQUE | identity |
| `referrals(referred_product_account_id)` partial UNIQUE `WHERE status NOT IN ('EXPIRED','REJECTED','REVOKED')` | I6 |
| `inbound_events(product_id, event_id)` UNIQUE | I4 |
| `payments(product_id, payment_id)`, `refunds(product_id, refund_id)`, `chargebacks(product_id, chargeback_id)` UNIQUE | business-key idempotency |
| `commissions(payment_id, referral_id, level)` UNIQUE | one commission per payment/referral |
| `journal_transactions(idempotency_key)` UNIQUE | exactly-once postings |
| `ledger_accounts(owner_type, owner_id, kind, currency)` UNIQUE | one account per kind |
| `credit_reservations(product_id, idempotency_key)`, `credit_refunds(product_id, idempotency_key)` UNIQUE | idempotent credit ops |
| `commission_rules(rule_id, version)` UNIQUE; exclusion constraint on `(scope_fingerprint, priority, tstzrange(effective_from, effective_until))` for ACTIVE rows | rules cannot tie (§9.2.3) |
| `approvals`: CHECK `approved_by <> requested_by` | maker-checker |
| `payments`: CHECK `amount_net_paid_minor = gross − discount − tax − credit_applied` and all `>= 0` | consistent amounts |
| `commissions`: CHECK `0 <= reversed_minor <= amount_minor` | reversals capped |
| `credit_reservations`: CHECK `reserved = from_credit_only + from_available`, `captured <= reserved` | I5 at row level |
| `ledger_entries`: deferred constraint trigger, per-transaction sum per currency = 0 | I1 |
| Insert-only trigger on all **[IO]** tables | I2 |

## Additions beyond §21

| Table | Why |
|---|---|
| `auth_handoff_tokens`, `otp_challenges` | single-use SSO handoff (§5.3) and OTP login need storage |
| `kyc_submissions` | KYC upload (§18) and KYC eligibility (§13) |
| `chargebacks` | ADR 0010 |
| `commission_state_transitions` | ADR 0006 (history of a mutable state) |
| `inbound_event_payloads`, `event_processing`, `event_processing_log` | ADR 0006 |
| `ledger_adjustments` | P15/P16 records with approvals (ADR 0007) |
| `credit_refunds` | §12 credit refund idempotency |
| `approvals` | replaces `payout_approvals` with one maker-checker table for payouts, adjustments and rule activation |
| `outbound_webhook_deliveries` | replaces `outbound_webhooks`; webhook URL and secret live on `products` |
| `reconciliation_runs` | ADR 0017 |
