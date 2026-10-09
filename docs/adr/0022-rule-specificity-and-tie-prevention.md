# 0022. Rule specificity score and database-enforced tie prevention

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 5

## Context

§9.2 ranks matching rules by specificity (`partner_id` > `campaign_id` > `partner_type` >
`plan_id` > `product_id` > global) then `priority`, and a remaining tie is a
configuration error the admin UI must refuse to save. The spec does not say how rules
with several scope fields compare (e.g. `campaign+plan` vs `campaign+product`), and
`billing_reason` is a scope field without a rank.

## Decision

- **Specificity score** is a bitmask over non-null scope fields:
  `partner_id 64 · campaign_id 32 · partner_type 16 · plan_id 8 · product_id 4 · billing_reason 2`
  (`level` is always 1 in v1 and does not count). Higher score wins. This is a
  lexicographic order over the spec's ranking, so `campaign+plan` (40) beats
  `campaign+product` (36), and any `partner_id` rule beats any rule without one.
- Then higher `priority` wins.
- **Tie theorem**: two ACTIVE rules can both match one payment with equal score only if
  they have the same set of non-null fields with the same values (every non-null field
  must equal the payment's value). So a tie ⇔ same **scope fingerprint**
  (`sha256` of the canonical non-null scope fields and values) + same `priority` +
  overlapping `[effective_from, effective_until)`.
- Enforced by a PostgreSQL exclusion constraint (`btree_gist`):
  `EXCLUDE USING gist (scope_fingerprint WITH =, priority WITH =, tstzrange(effective_from, effective_until) WITH &&) WHERE (status = 'ACTIVE')`.
  The admin API maps the violation to `409 COMMISSION_RULE_TIE`.
- Resolution still checks for ties at runtime (defence in depth) and marks the payment
  `NEEDS_REVIEW` with an alert if one is ever found (§9.2.3).

## Consequences

- Rule ties are impossible to save, from the UI, the API or the CLI.
- Requires the `btree_gist` extension (standard contrib, available on managed Postgres).
