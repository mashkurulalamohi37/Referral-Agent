# 0002. Celery tasks run async domain code on a per-process event loop

- Status: Accepted
- Date: 2026-10-08

## Context

§2 fixes FastAPI with async SQLAlchemy (`asyncpg`) for the API and Celery for background
jobs, and leaves open how tasks access the database. Celery tasks are synchronous.
The options:

1. **Sync engine in workers** (`psycopg` + sync `Session`). Domain services would need a
   sync twin, or would have to be written twice. Money logic (commissions, ledger,
   credits) would exist in two variants: unacceptable under §0.3.
2. **`asyncio.run()` per task.** Simple, but creates a new event loop and a new
   connection pool per task; `asyncpg` pools are bound to their loop.
3. **One event loop per worker process**, created at `worker_process_init`, with one
   async engine bound to it. Each task runs `loop.run_until_complete(handler(...))`.

## Decision

Option 3.

- All domain code is `async` and is written once, in each module's `service.py`.
- `app/worker/runtime.py` owns a process-global event loop and async engine, created in
  the `worker_process_init` signal and disposed in `worker_process_shutdown`.
- Workers use the `prefork` pool (one loop per child process). The `gevent`/`eventlet`
  pools are not supported.
- Tasks are thin wrappers: `run_async(coro)` → open a session, call a service function,
  commit. Tasks never contain business logic.
- Every task is idempotent (§2). Task arguments are IDs, never ORM objects.

## Consequences

- One implementation of money logic serves both API and workers.
- Tests can call service functions directly without Celery.
- A worker child handles one task at a time; scale with `--concurrency`.
- If a future move to an async-native queue (arq, Dramatiq with asyncio) is wanted, task
  wrappers are the only code that changes.
