# 0001. Record decisions; spec v2 is the baseline

- Status: Accepted
- Date: 2026-10-08

## Context

`docs/spec-v2.md` is the build brief. Section 0.2 requires every non-trivial design
decision, and every resolution of an ambiguity, to be recorded as an ADR. The Phase 0
review of the spec found contradictions and gaps (listed in
`docs/phase-reports/phase-0.md`).

## Decision

- `docs/spec-v2.md` is the baseline and is not edited in place.
- Changes and clarifications to the spec are made only through ADRs. When an ADR
  conflicts with the spec, the ADR wins once it is `Accepted`.
- ADRs that change business behaviour (money, attribution, privacy) start as
  `Proposed`. Until accepted, implementation uses the ADR's decision as the default,
  as Section 24 does for open questions.
- Section references in ADRs (`§9.4`) point at `docs/spec-v2.md`.

## Consequences

- Reviewers read the spec plus the ADR index to know the full contract.
- A future spec v3 can fold accepted ADRs back into one document.
