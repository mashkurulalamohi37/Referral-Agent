# 0018. Production-grade operator CLI before the admin panel

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 8

## Context

§23 starts real product integrations after Phase 8, in parallel with Phases 9+. Creating
products, plans, API clients and commission rules is an admin-panel task (Phase 10).
§25 mentions a seed CLI for local dev only.

## Decision

- `python -m app.cli` (Typer) is a supported operator tool, not just a dev seed:
  `products create|update`, `plans create`, `api-clients create|rotate|revoke`,
  `rules create|simulate|close`, `commissions hold|release`, `events replay`,
  `users grant-role`, `reconcile ledger`.
- Every CLI command calls the same `service.py` functions as the admin API, writes the
  same audit log entries (actor = `cli:{os_user}` plus a required `--reason`), and
  respects maker-checker by creating a pending approval rather than executing.
- Secrets created by the CLI are printed once and never logged.

## Consequences

- PulsePOS can be onboarded after Phase 8 without waiting for the admin panel.
- The admin panel in Phase 10 is a UI over existing, already-audited service calls.
