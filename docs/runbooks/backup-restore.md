# Operational Runbook: Database Backup and Restore Drill

This runbook documents procedures for routine backups, disaster recovery, and point-in-time recovery (PITR) for PostgreSQL and Redis (§22.4).

---

## 1. Daily & Continuous Backup Strategy

- **PostgreSQL 16**: Continuous WAL archiving to S3/Cloud Storage + daily `pg_dump` snapshot.
- **Redis 7**: AOF (Append-Only File) enabled with `fsync everysec` + RDB snapshot persistence every 60 seconds if ≥ 1000 keys change.

---

## 2. Backup Execution

### 2.1 Postgres Snapshot
```bash
docker compose exec postgres pg_dump -U postgres -d referral -Fc -f /var/lib/postgresql/data/backup_$(date +%Y%m%d_%H%M%S).dump
```

### 2.2 Redis Backup
```bash
docker compose exec redis redis-cli bgsave
```

---

## 3. Disaster Recovery Drill (Restore Verification)

1. **Stop platform services**:
   ```bash
   docker compose stop api worker beat
   ```
2. **Recreate PostgreSQL database from backup**:
   ```bash
   docker compose exec postgres dropdb -U postgres --if-exists referral
   docker compose exec postgres createdb -U postgres referral
   docker compose exec postgres pg_restore -U postgres -d referral /var/lib/postgresql/data/backup_latest.dump
   ```
3. **Run database verification**:
   ```bash
   docker compose run --rm migrate
   ```
4. **Restart application stack**:
   ```bash
   docker compose start api worker beat
   ```
5. **Verify healthcheck**:
   ```bash
   curl -i http://127.0.0.1:8000/v1/health
   ```
