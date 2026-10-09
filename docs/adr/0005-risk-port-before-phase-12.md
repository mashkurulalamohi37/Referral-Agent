# 0005. Risk assessment port available from Phase 5

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 5

## Context

The commission lifecycle (Phase 5) has an `ON_HOLD` branch driven by HIGH risk, and
payout eligibility (Phase 11) checks for open HIGH risk cases. The risk module is built
in Phase 12. §0.3 forbids stubs in money paths.

## Decision

- `risk/service.py` defines its public interface in Phase 5:
  - `assess_commission(ctx) -> RiskVerdict` (`LOW | MEDIUM | HIGH | BLOCKED`, reasons)
  - `has_open_high_case(user_id) -> bool`
  - `is_blocked(user_id) -> bool`
- Phases 5–11 ship `RuleSetRiskAssessor` with an **empty rule set**, which returns `LOW`.
  The self-referral hard block (§7.3) is part of attribution, not of the assessor, and
  is fully implemented in Phase 3.
- The commission lifecycle code for `ON_HOLD` (hold, clear to PENDING/AVAILABLE, reject)
  is complete in Phase 5 and tested with a test assessor that returns HIGH.
- Admins can place and clear holds manually from Phase 5 via service functions (and the
  operator CLI, ADR 0018) so the path is reachable before Phase 12.
- Phase 12 adds rules, scoring, signal hashing analytics and the case workflow behind the
  same interface.

## Consequences

- No placeholder logic exists in the money path: the hold transitions are real, only the
  set of rules that trigger them grows later.
