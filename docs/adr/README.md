# Architecture Decision Records

Each ADR records one non-trivial decision: context, decision, consequences.
Status is one of `Proposed` (needs business/tech review), `Accepted`, `Superseded by NNNN`.

ADRs marked **Proposed** change or fill gaps in `docs/spec-v2.md` and need sign-off
before the phase that depends on them starts (see the "Blocks phase" line).

| ADR | Title | Status | Blocks phase |
|---|---|---|---|
| [0001](0001-record-decisions-and-spec-baseline.md) | Record decisions; spec v2 is the baseline | Accepted | — |
| [0002](0002-celery-database-access.md) | Celery tasks run async domain code on a per-process event loop | Accepted | 1 |
| [0003](0003-ids-time-and-money-primitives.md) | UUIDv7, time and money primitives | Accepted | 1 |
| [0004](0004-mvp-acceptance-scope.md) | MVP acceptance scenario stops before withdrawal | Proposed | 5 |
| [0005](0005-risk-port-before-phase-12.md) | Risk assessment port available from Phase 5 | Accepted | 5 |
| [0006](0006-immutability-scope.md) | Immutability scope: insert-only tables vs processing state | Accepted | 1 |
| [0007](0007-ledger-sign-convention-and-postings.md) | Ledger sign convention and complete posting table | Proposed | 5 |
| [0008](0008-reversal-allocation.md) | Reversal allocation across split rewards and held funds | Proposed | 6 |
| [0009](0009-refund-proration.md) | Cumulative refund proration | Proposed | 6 |
| [0010](0010-commission-lifecycle-completion.md) | Commission lifecycle gaps: partial pending refunds, holds, failures, chargebacks | Proposed | 5 |
| [0011](0011-late-credit-capture.md) | Credit capture after reservation expiry or amount mismatch | Proposed | 7 |
| [0012](0012-event-ordering-key.md) | Event ordering lock is per product account | Accepted | 4 |
| [0013](0013-attribution-grace-and-retry.md) | Attribution grace window and durable retry | Proposed | 3 |
| [0014](0014-referral-conversion-window.md) | Referral `EXPIRED` uses a conversion window | Proposed | 3 |
| [0015](0015-user-registered-vs-attribution.md) | `user.registered` is informational; attribution only via API | Accepted | 3 |
| [0016](0016-healora-visibility-default.md) | Healora referrer visibility defaults to `NONE` | Proposed | 9 |
| [0017](0017-missed-event-reconciliation.md) | Product payment reconciliation to catch missed events | Proposed | 13 |
| [0018](0018-operator-cli-before-admin-panel.md) | Production-grade operator CLI before the admin panel | Accepted | 8 |
| [0019](0019-naming-product-slug.md) | Products are addressed by `slug`, not `code` | Accepted | 2 |
| [0020](0020-frontend-stacks.md) | Two frontend stacks kept, revisit before Phase 9 | Proposed | 9 |
| [0021](0021-tier-count-timing.md) | Tier counts are evaluated at commission creation | Accepted | 5 |
| [0022](0022-rule-specificity-and-tie-prevention.md) | Rule specificity score and DB-enforced tie prevention | Accepted | 5 |
