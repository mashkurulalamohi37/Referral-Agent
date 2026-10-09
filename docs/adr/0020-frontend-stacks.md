# 0020. Two frontend stacks kept, revisit before Phase 9

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 9

## Context

§2 locks React for the customer portal and Quasar/Vue for the admin panel, and notes
that this doubles UI maintenance (two component libraries, two state/query stacks, two
lint/test setups, two hiring profiles).

## Decision

- Keep both stacks as specified, because they were explicitly requested.
- Reduce the cost where possible:
  - one generated TypeScript API client (from `openapi.yaml`) shared by both apps as a
    workspace package;
  - shared Zod schemas are not reused in the admin (Vue uses its own validation), so the
    OpenAPI types are the single source of truth;
  - one Playwright setup at the repo root covering both apps.
- **Revisit before Phase 9 starts.** If no strong reason exists (existing Quasar team,
  existing admin components), switch the admin panel to React + a React admin kit and
  supersede this ADR.

## Consequences

- No impact on Phases 0–8 (backend and SDK only).
