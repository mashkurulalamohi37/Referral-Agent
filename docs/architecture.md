# Architecture

Baseline: [`spec-v2.md`](spec-v2.md). Decisions: [`adr/`](adr/README.md). Data model:
[`erd.md`](erd.md). API: [`openapi.yaml`](openapi.yaml), [`api.md`](api.md). Events:
[`events.md`](events.md). Threats: [`threat-model.md`](threat-model.md).

## 1. Deployment view

```mermaid
flowchart LR
    subgraph Products
        PB[Product backend<br/>PulsePOS / Healora / ...]
        PF[Product frontend]
    end
    Browser((Referrer / customer browser))
    subgraph Platform
        NGX[Nginx<br/>TLS, routing, rate limits]
        API[API image<br/>FastAPI modular monolith]
        WRK[Worker image<br/>Celery workers]
        BEAT[Celery Beat]
        PG[(PostgreSQL 16)]
        RD[(Redis 7)]
        PORTAL[Portal - React]
        ADMIN[Admin - Quasar]
    end
    Browser -- "/r/{code}" --> NGX
    Browser --> PORTAL
    PF -- "ref, rt" --> PB
    PB -- "signed API + events" --> NGX
    NGX --> API
    API --> PG
    API --> RD
    WRK --> PG
    WRK --> RD
    BEAT --> RD
    WRK -- "outbound webhooks" --> PB
    PORTAL --> NGX
    ADMIN --> NGX
```

- One API image, one worker image (same codebase, different entrypoint). Beat runs from
  the worker image with a single replica.
- Redis: Celery broker, rate-limit buckets, short-lived caches. **Never** a source of
  truth for money; losing Redis loses no financial state (outbox rows in Postgres are
  re-dispatched).

## 2. Request and event processing inside the monolith

```mermaid
flowchart TB
    R[HTTP route] --> S1[module service.py]
    S1 -->|same DB transaction| DB[(Postgres)]
    S1 -->|domain event| BUS[in-process bus]
    BUS -->|sync handlers in same tx| S2[other module service.py]
    BUS -->|async reactions| OB[outbox row, same tx]
    OB --> D[outbox dispatcher task]
    D --> T[Celery task -> service.py]
    D --> N[notification / webhook send]
```

- A module calls another only through `service.py` (§3). An import-linter contract in CI
  enforces it.
- Domain events with a **synchronous** handler run inside the publishing transaction
  (e.g. `PaymentRecorded` → commissions creates a commission → ledger posts P1).
  Everything else goes through the outbox, written in the same transaction.
- Inbound events: `POST /v1/events` only verifies, validates, and inserts
  `inbound_events` + `event_processing` + payload (target p95 < 200 ms). A
  `process_event` task does the work under the ordering-key advisory lock (ADR 0012).

## 3. Acceptance A: earn and reverse (Phase 5 exit, ADR 0004)

```mermaid
sequenceDiagram
    autonumber
    actor Rahim
    actor Karim
    participant HL as Healora backend
    participant P as Platform API
    participant W as Platform worker
    participant DB as Postgres

    HL->>P: POST /v1/referrers/enroll {external_user_id: HLR-RAHIM}
    P->>DB: user, product_account (linked), ledger accounts, code RAHIM7K3Q
    P-->>HL: 201 {code, link, portal_url}

    Karim->>P: GET /r/RAHIM82?product=healora
    P->>DB: insert referral_click (hashed IP, UTM)
    P-->>Karim: 302 → healora signup_url?ref=RAHIM82&rt=<JWS>
    Karim->>HL: sign up (ref, rt stored by frontend)
    HL->>P: POST /v1/attributions {HLR-456, registered_at, code, token, signals}
    P->>P: verify token, code precedence, window, grace, self-referral (§7.3)
    P->>DB: product_account HLR-456, referral ATTRIBUTED (partial unique, I6)
    P-->>HL: 201 attribution

    Karim->>HL: pay ৳2,000 Premium
    HL->>P: POST /v1/events payment.succeeded (signed)
    P->>DB: inbound_event + event_processing RECEIVED
    P-->>HL: 202 {platform_event_id}
    W->>DB: lock ordering key (healora, HLR-456)
    W->>DB: payment row (unique business key)
    W->>W: resolve rule (10%), base = net paid 200000
    W->>DB: commission PENDING 20000 + snapshot (I8)
    W->>DB: journal P1: Dr commission_expense 20000 / Cr Rahim pending 20000
    W->>DB: referral CONVERTED, outbox: notify "commission earned"

    Note over W,DB: Beat every 15 min: eligible_at = paid_at + 14 days reached, no hold
    W->>DB: commission AVAILABLE, journal P2: Dr pending 20000 / Cr available 20000

    Rahim->>P: GET /v1/me/wallet
    P-->>Rahim: available ৳200

    HL->>P: payment.refunded (full, ৳2,000)
    W->>DB: refund row, cumulative ratio = 1 (ADR 0009)
    W->>DB: commission REVERSED, journal P4: Dr available 20000 / Cr commission_expense 20000
```

### Worked ledger for Acceptance A (minor units, BDT)

| Step | Txn | Entries | Rahim pending | Rahim available | commission_expense |
|---|---|---|---|---|---|
| Payment | P1 | +20000 `commission_expense`, −20000 `pending` | 20000 | 0 | 20000 |
| Confirm | P2 | +20000 `pending`, −20000 `available` | 0 | 20000 | 20000 |
| Refund | P4 | +20000 `available`, −20000 `commission_expense` | 0 | 0 | 0 |

(Displayed user balances are `−SUM(entries)`, ADR 0007.) Every row sums to zero (I1),
and balances equal the sum of entries (I3).

## 4. Acceptance B: spend as subscription credit (Phase 7 exit)

```mermaid
sequenceDiagram
    autonumber
    actor Rahim
    participant PP as PulsePOS backend
    participant P as Platform API
    participant DB as Postgres

    Rahim->>PP: checkout, plan ৳1,150 incl. tax, "use referral credit"
    PP->>P: GET /v1/credits/balance?external_user_id=PP-RAHIM&currency=BDT
    P-->>PP: spendable 20000, cap 100%
    PP->>P: POST /v1/credits/reservations {requested 20000, order_ref, idempotency_key}
    P->>DB: lock Rahim's accounts (ordered by id), check spendable
    P->>DB: reservation RESERVED, P6: Dr available 20000 / Cr reserved 20000
    P-->>PP: {reservation_id, reserved_amount 20000, expires_at +15 min}
    PP->>PP: charge ৳950 (1,150 − 200)
    alt charge succeeds
        PP->>P: POST /v1/credits/reservations/{id}/capture {applied 20000, payment_id}
        P->>DB: P7: Dr reserved 20000 / Cr credit_redeemed:pulsepos 20000, state CAPTURED
        PP->>P: payment.succeeded {credit_applied_amount 20000, credit_reservation_id}
        P->>DB: capture already done → no-op, commission base excludes credit (§9.3)
    else charge fails or abandoned
        PP->>P: POST /v1/credits/reservations/{id}/release
        P->>DB: P8: Dr reserved 20000 / Cr available 20000, state RELEASED
    end
    Note over P,DB: If neither arrives: expiry job releases at expires_at + 10 min.<br/>A later capture becomes a late capture (P9, ADR 0011).
```

## 5. Acceptance C: withdrawal (Phase 11 exit)

```mermaid
sequenceDiagram
    autonumber
    actor Rahim
    actor FA1 as Finance admin 1
    actor FA2 as Finance admin 2
    participant P as Platform
    participant DB as Postgres

    Rahim->>P: POST /v1/me/payouts {method bKash, 50000} + Idempotency-Key
    P->>P: eligibility: verified email+phone, KYC, ≥ min_payout, no HIGH case, not negative
    P->>DB: payout REQUESTED, P11: Dr available / Cr payout_hold
    FA1->>P: approve
    alt amount ≥ dual_approval_threshold
        FA2->>P: approve (must differ from FA1)
    end
    P->>DB: payout APPROVED → PROCESSING (manual provider)
    FA1->>P: mark-paid {transfer reference}
    P->>DB: P12: Dr payout_hold 50000 / Cr payout_clearing (net) + tax_withholding_payable (tax)
    P->>DB: payout PAID, outbox: notify Rahim
```

## 6. Event intake and retry states

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: verified + persisted (202)
    RECEIVED --> PROCESSING: worker takes ordering-key lock
    PROCESSING --> PROCESSED: effects committed
    PROCESSING --> IGNORED: not referred / not eligible
    PROCESSING --> WAITING_DEPENDENCY: referenced payment/subscription unknown
    WAITING_DEPENDENCY --> RECEIVED: backoff retry (≤ 72 h)
    WAITING_DEPENDENCY --> DEAD_LETTER: 72 h elapsed
    PROCESSING --> FAILED: unexpected error
    FAILED --> RECEIVED: retry (≤ 10)
    FAILED --> DEAD_LETTER: retries exhausted
    DEAD_LETTER --> RECEIVED: admin replay (audited)
```

## 7. Concurrency rules (summary)

| Concern | Mechanism |
|---|---|
| Duplicate event delivery (I4) | `inbound_events(product_id, event_id)` unique insert; business-key uniques; ledger `idempotency_key` unique |
| Concurrent events for one customer | `pg_advisory_xact_lock(ordering_key)` (ADR 0012) |
| Balance changes (I5) | One DB transaction; `SELECT … FOR UPDATE` on affected `ledger_accounts` rows in ascending id order; balance check after lock |
| Commission state | Row lock on `commissions` + allowed-transition table |
| Celery redelivery | Every task idempotent; tasks take IDs; effects keyed by unique constraints |
| Beat overlap | Jobs take a named advisory lock (`pg_try_advisory_lock`) and skip if held |
