# 0003. UUIDv7, time and money primitives

- Status: Accepted
- Date: 2026-10-08

## Context

§2 requires UUIDv7 primary keys, UTC `timestamptz`, and integer minor-unit money with
`Decimal` intermediates and `ROUND_HALF_UP` once at the end. PostgreSQL 16 has no
built-in `uuidv7()` and Python 3.12's `uuid` module has no `uuid7()`.

## Decision

**IDs**
- `app/core/ids.py` implements RFC 9562 UUIDv7 (48-bit Unix ms timestamp, version and
  variant bits, 74 random bits from `secrets`), monotonic within a process for
  same-millisecond calls. Unit-tested for version/variant bits and ordering.
- IDs are generated in the application, not by a DB default.

**Time**
- `app/core/clock.py` exposes `now() -> datetime` (aware, UTC). All code calls it;
  tests freeze it. Naive datetimes are rejected at the Pydantic boundary.

**Money**
- `app/core/money.py` defines `Money(amount_minor: int, currency: str)`, immutable.
  Arithmetic between different currencies raises.
- Currency exponents come from a table (`BDT: 2`, `USD: 2`, `JPY: 0`, …). Only BDT is
  enabled in v1 (Q13).
- Calculations use `Decimal` with a local context (precision 38) and finish with one
  `quantize(Decimal(1), ROUND_HALF_UP)` on the minor-unit value.
- `allocate(total, weights)` splits an integer amount by weights using the
  largest-remainder method so parts always sum exactly to the total. Used by reward
  splits and reversals (ADR 0008).
- `float` is banned in money paths: a `ruff` rule plus a unit test that scans the money
  modules' AST for float literals and `float(` calls.

## Consequences

- No database extension is needed.
- Money rounding behaviour lives in one module with exhaustive edge-case tests.
