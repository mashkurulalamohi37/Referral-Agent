# Production Deployment & Infrastructure Guide

This guide details the production deployment, infrastructure topology, security configuration, and operational workflows for the Centralized Referral & Commission Platform (§1, §41, §51).

---

## 1. System Architecture & Topology

The production stack is organized into decoupled, horizontally scalable layers:

```text
                                Internet (HTTPS / Port 443)
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    Nginx Reverse Proxy      │
                             │  (TLS, Rate-Limiting, Gzip) │
                             └──────────────┬──────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
                    ▼                                               ▼
     ┌─────────────────────────────┐                 ┌─────────────────────────────┐
     │    FastAPI API Nodes        │                 │    Celery Background        │
     │  (Gunicorn / Uvicorn)       │                 │    Workers & Beat Scheduler │
     └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                    │                                               │
                    ├───────────────────────┬───────────────────────┤
                    ▼                       ▼                       ▼
     ┌─────────────────────────────┐ ┌─────────────┐ ┌─────────────────────────────┐
     │    PostgreSQL 16 DB         │ │   Redis 7   │ │  Outbound Webhook Hub       │
     │ (Immutable Ledger & Trigger)│ │(Broker/Rate)│ │  (Transactional Outbox)     │
     └─────────────────────────────┘ └─────────────┘ └─────────────────────────────┘
```

---

## 2. Docker & Container Orchestration

The platform provides multi-stage, hardened Docker images and Compose configurations:

- `docker-compose.yml`: Base container definitions.
- `docker-compose.dev.yml`: Development overrides (hot reloading, debug logs, local ports).
- `docker-compose.prod.yml`: Production deployment profile (resource limits, production Nginx TLS, restart policies).

### 2.1 Production Container Launch

```bash
# 1. Populate production environment variables
cp .env.example .env
# Edit .env and supply production secrets (minimum 32 characters, no 'dev-only')

# 2. Place SSL certificates in the designated certificate directory
mkdir -p /etc/referral/tls
cp fullchain.pem /etc/referral/tls/
cp privkey.pem /etc/referral/tls/

# 3. Launch production stack in detached mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 3. Database Role Separation & Security

To protect the immutable double-entry ledger from tampering (Threat Model T1, Invariant I2), the database uses role-level access controls:

1. **`referral_owner`** (Schema Owner):
   - Used exclusively by migration jobs (`alembic upgrade head`).
   - Owns all tables, indexes, and database triggers.
2. **`referral_app`** (DML Application User):
   - Used by the FastAPI runtime and Celery workers.
   - Granted `SELECT`, `INSERT`, `UPDATE` on tables.
   - **Cannot** disable database triggers (`trg_ledger_entries_immutable`, `trg_audit_logs_immutable`) or alter schemas.

### 3.1 Migration Execution

```bash
# Run schema migrations in an ephemeral migration container:
docker compose run --rm migrate
```

---

## 4. Environment Variables Checklist

Ensure the following variables are configured in `.env` before production deployment:

| Variable | Description | Security Requirement |
|---|---|---|
| `APP_ENV` | Environment identifier (`prod` or `staging`) | Must be `prod` |
| `DATABASE_URL` | Async connection string for `referral_app` | Strong secret |
| `MIGRATION_DATABASE_URL` | Async connection string for `referral_owner` | Strong secret |
| `REDIS_URL` | Redis connection URL with auth | Strong password |
| `JWT_SIGNING_KEY` | Secret used to sign user JWT access tokens | $\ge 32$ random chars |
| `ATTRIBUTION_TOKEN_KEY` | Secret used for JWS attribution tokens | $\ge 32$ random chars |
| `SIGNAL_HASH_PEPPER` | Salt used for HMAC risk signal hashing | $\ge 32$ random chars |
| `PAYOUT_DETAILS_ENCRYPTION_KEY` | AES-256-GCM key (32 bytes base64) | Secure key management |
| `SECRETS_ENCRYPTION_KEY` | AES-256-GCM key for product signing secrets | Secure key management |

---

## 5. Health Checks & Verification

After deployment, verify that all components are healthy and operational:

```bash
# 1. Basic liveness check
curl -f http://127.0.0.1:8080/v1/health

# 2. Readiness check (verifies database connectivity, migrations, and Redis)
curl -f http://127.0.0.1:8080/v1/ready
# Expected: {"database":"ok","redis":"ok","migrations":"ok"}
```

---

## 6. Operational Runbooks

For maintenance, disaster recovery, and operational procedures, consult the runbooks:

- [Database Backup & Restore Drill](runbooks/backup-restore.md)
- [Event Dead-Letter Replay](runbooks/event-dead-letter-replay.md)
- [Payout Disbursement Protocol](runbooks/payout-disbursement.md)
- [Incident Response & Escalation](runbooks/incident-response.md)
