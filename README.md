# Centralized Referral & Commission Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=flat&logo=vue.js&logoColor=white)](https://vuejs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-grade, standalone SaaS referral attribution, commission calculation, double-entry wallet ledger, subscription credit management, and payout disbursement platform. Built for multi-tenant B2B and consumer SaaS ecosystems, connected via signed webhook events and polyglot SDKs.

---

## 🌟 Key Highlights & Core Capabilities

- **Modular Monolith Architecture**: Clean separation of concerns with strictly enforced domain service boundaries (`app.<module>.service`).
- **High-Precision Double-Entry Ledger**: Full compliance with financial double-entry bookkeeping (Asset, Liability, Equity, Revenue, Expense). Exact integer math in minor currency units (`BIGINT` Poisha / Cents) with **zero floating-point operations**.
- **Cryptographic Attribution Engine**: Signed JWS cross-domain attribution tokens, Crockford Base32 vanity referral codes, collision-resistant generation, and multi-signal self-referral prevention.
- **Rule Specificity Scoring (ADR 0022)**: Deterministic bitmask specificity resolution for commission rules across partner tiers, campaigns, plans, billing reasons, and products.
- **Two-Phase Subscription Credits**: In-app wallet credit engine featuring two-phase commit reservation (`reserve` $\rightarrow$ `capture` $\rightarrow$ `release` $\rightarrow$ `refund`).
- **Maker-Checker Payout Disbursement**: Multi-tier approval workflows for disbursements (bKash, Nagad, Bank Transfer) with automated dual-approval thresholds (৳50,000+), Payout Hold ledger segregation, and bulk CSV settlement exports.
- **Fraud & Risk Defense Engine**: Privacy-preserving HMAC-SHA256 peppered risk signal hashing (device fingerprint, IP subnet `/24` & `/48`, email/phone match, payment instrument fingerprint).
- **Transactional Outbox & Ingestion Worker**: Resilient event broker with per-key PostgreSQL advisory locking, exponential backoff for `WAITING_DEPENDENCY` events, dead-letter storage, and idempotent replaying.
- **Dual Modern Frontend Interfaces**:
  - **Customer / Partner Portal**: React 18 + Vite + TypeScript (Dashboard, Custom Vanity Codes, Wallet Balances, Payout Requests, Embeddable Web Components).
  - **Admin & Operations Console**: Vue 3 + Pinia + TypeScript (Commission Rule Specificity Simulator, Real-Time Inbound Event Console, Maker-Checker Review Queue, Risk Analyst Console, Audit Logs).
- **Polyglot SDKs & Product Simulators**: Python 3 SDK, TypeScript/Node.js Server SDK, Browser Embed JS SDK, and live simulator for sample apps (*PulsePOS* & *Healora*).

---

## 🏗️ Architecture Overview

```
                          ┌───────────────────────────┐
                          │   External SaaS Products  │
                          │   (PulsePOS, Healora, ..) │
                          └─────────────┬─────────────┘
                                        │ Signed HMAC Events / REST API
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy & Rate Limiter                        │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │   FastAPI Web API     │               │   Celery Workers      │
        │  (app/api & services) │               │  (Outbox / Beat / DLQ)│
        └───────────┬───────────┘               └───────────┬───────────┘
                    │                                       │
                    ├───────────────────┬───────────────────┤
                    ▼                   ▼                   ▼
        ┌───────────────────────┐┌──────────────┐┌───────────────────────┐
        │   PostgreSQL 16 DB    ││   Redis 7    ││  Signed Webhook Hub   │
        │ (Double-Entry Ledger) ││(Broker/Cache)││  (Transactional Out)  │
        └───────────────────────┘└──────────────┘└───────────────────────┘
```

### Module Boundaries (`backend/app/`)
Cross-module communication is strictly restricted to service-level public functions to maintain high cohesion and low coupling:

```text
app/
├── identity/       # Users, Authentication, API Keys, RBAC, Partner Profiles
├── catalog/        # Multi-Product Catalog, Product Accounts, Plan Codes
├── referrals/      # Vanity Codes, Clicks, Attributions, JWS Tokens
├── events/         # HMAC Ingestion, Idempotency, Transactional Outbox
├── subscriptions/  # Subscription Fact Ingestion, Payment Facts, Refund Facts
├── commissions/    # Specificity Scoring Engine, Calculations, Maturity Lifecycle
├── ledger/         # Immutable Double-Entry Ledger, Balance Queries, Holds
├── credits/        # Two-Phase In-App Wallet Credits (Reserve, Capture, Release)
├── payouts/        # Maker-Checker Approvals, Disbursement Methods, CSV Exports
├── risk/           # HMAC Signal Hashing, Fraud Evaluation, Hold Rules
├── notifications/  # Webhook Dispatcher, Notification Queues
└── reporting/      # Admin Analytics, Daily Payment Reconciliation (ADR 0017)
```

---

## 🚀 5-Minute Quickstart

### Prerequisites
- [Docker](https://www.docker.com/) & [Docker Compose v2](https://docs.docker.com/compose/)
- Alternatively for local native development: Python 3.12+, Node.js 20+, PostgreSQL 16, Redis 7.

### Running with Docker Compose (Recommended)

1. **Clone the repository and prepare environment variables**:
   ```bash
   cp .env.example .env
   ```

2. **Start the platform services**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --wait
   ```

3. **Verify service readiness**:
   ```bash
   curl http://localhost:8080/v1/ready
   # Response: {"database":"ok","redis":"ok","migrations":"ok"}
   ```

4. **Access the web consoles**:
   - **Interactive API Documentation (Swagger)**: [http://localhost:8000/v1/docs](http://localhost:8000/v1/docs)
   - **Partner Portal**: [http://localhost:3000](http://localhost:3000)
   - **Admin Operations Console**: [http://localhost:3001](http://localhost:3001)

---

## 🧪 Testing, Quality & Architecture Verification

The platform maintains a 100% automated test pass rate with strict architectural boundary enforcement.

### Running Backend Unit & Contract Tests

```bash
# Enter backend environment
cd backend

# Run the complete test suite
pytest tests/

# Verify strict modular architecture boundaries (0 violations)
pytest tests/unit/test_architecture.py

# Verify schema contracts across all 14 inbound JSON events
python ../tools/check_contracts.py
```

### Static Analysis & Type Checking

```bash
# Code format & linting
ruff check .
ruff format --check .

# Strict type verification
mypy app/
```

---

## 📁 Repository Layout

```text
referral-platform/
├── backend/
│   ├── app/                      # Domain modules (identity, ledger, commissions, etc.)
│   ├── migrations/               # Alembic database migrations
│   ├── tests/                    # Comprehensive unit, integration & architecture tests
│   ├── Dockerfile                # Multi-stage production container image
│   └── pyproject.toml            # Python dependencies and tooling configuration
├── frontend/
│   ├── portal/                   # React 18 + Vite Customer & Partner Portal
│   └── admin/                    # Vue 3 + Pinia Admin & Operations Console
├── sdk/
│   ├── python/                   # Python 3 Client SDK
│   └── typescript/
│       ├── server/               # Node.js Server SDK (Webhook verification & API client)
│       └── browser/              # Embeddable Web Components (<referral-code-input>)
├── deploy/
│   ├── nginx/                    # Nginx reverse proxy configuration & rate limits
│   └── postgres/init/            # PostgreSQL database roles and init scripts
├── docs/
│   ├── spec-v2.md                # System Implementation Specification
│   ├── architecture.md           # High-Level Architecture & Deployment View
│   ├── erd.md                    # Database Schema & Entity Relationship Diagram
│   ├── threat-model.md           # STRIDE Threat Model & Mitigation Matrix
│   ├── adr/                      # Architectural Decision Records (ADR 0001 - ADR 0022)
│   ├── events/                   # JSON Schema definitions for all 14 event contracts
│   ├── runbooks/                 # Operational & Disaster Recovery Runbooks
│   └── phase-reports/            # Delivery summary reports for Phases 0 to 14
├── tools/
│   ├── check_contracts.py        # Automated contract validator
│   └── product-simulator/        # Interactive SaaS event simulation tool
└── docker-compose.yml            # Base docker-compose stack definition
```

---

## 📖 Operational Runbooks & Production Guides

Full runbooks are provided in `docs/runbooks/`:

- **[Database Backup & Disaster Recovery Drill](docs/runbooks/backup-restore.md)**: PostgreSQL continuous WAL archiving, snapshot exports, Redis persistence, and point-in-time recovery (PITR).
- **[Event Dead-Letter Inspection & Replay](docs/runbooks/event-dead-letter-replay.md)**: Triage workflow for `WAITING_DEPENDENCY` events, error inspection, and idempotent replay execution.
- **[Payout Disbursement & Maker-Checker Protocol](docs/runbooks/payout-disbursement.md)**: Dual approval enforcement for disbursements above ৳50,000, bank/mobile wallet exports, and settlement reconciliation.
- **[Incident Response & Emergency Procedures](docs/runbooks/incident-response.md)**: Severity classifications (SEV-1 to SEV-3), ledger freezing commands, and communication escalation matrix.

---

## 🔒 Financial Invariants & Security Guarantees

1. **I1 (No Negative Balances)**: User wallet available balances and credit balances can never drop below zero.
2. **I2 (Immutable Double-Entry Ledger)**: Database ledger records and audit logs are append-only; updates and deletions are blocked by PostgreSQL database triggers.
3. **I3 (Deterministic Integer Money Math)**: All currency calculations are performed in integer minor units (`BIGINT`) with exact integer arithmetic (`mul_div_round` with single half-up rounding). Floating-point arithmetic is strictly prohibited.
4. **I4 (Zero Ambiguity Rule Ties)**: The commission engine evaluates rule specificity bitmasks (ADR 0022) and rejects ambiguous ties with an explicit error instead of silent fallback.
5. **I5 (Strict Maker-Checker Separation)**: Payout approvals require a distinct actor ID (`actor_id != user_id`) to prevent self-approval.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
