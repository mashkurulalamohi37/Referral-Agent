# 0007. Ledger sign convention and complete posting table

- Status: Proposed
- Date: 2026-10-08
- Blocks phase: 5

## Context

§10.2 lists postings but omits: credit refund (§12), tax withholding (§13), chargebacks,
negative-balance netting (§10.4), payout returns, and what clears
`platform:payout_clearing`. It also does not fix a sign convention, so "balance" is
ambiguous for accounts on different sides.

## Decision

### Sign convention

- `ledger_entries.amount_minor` is signed: **positive = debit, negative = credit**.
- I1: for every journal transaction, `SUM(amount_minor)` grouped by currency is `0`.
  Enforced by a deferred constraint trigger on `ledger_entries` that checks the
  transaction at commit, and by the ledger service before insert.
- Each account has a `normal_side`:

| Account | Normal side | Displayed balance |
|---|---|---|
| `user:pending`, `user:available`, `user:credit_only`, `user:reserved`, `user:payout_hold` | credit (liability to user) | `-SUM(amount)` |
| `platform:commission_expense`, `platform:writeoff` | debit (expense) | `SUM(amount)` |
| `platform:credit_redeemed:{product}` | credit (value owed to/settled with product, Q10) | `-SUM(amount)` |
| `platform:payout_clearing` | credit (cash paid out, reconciled against bank/provider) | `-SUM(amount)` |
| `platform:tax_withholding_payable` (new) | credit | `-SUM(amount)` |

A user balance below zero means the user owes the platform (§10.4).

### Derived balances (portal, §10.5)

- `negative` ⇔ `available < 0` or `credit_only < 0`.
- `withdrawable = available` if not `negative`, else `0`.
- `spendable_credit = max(0, available + credit_only)`. A negative available balance
  reduces what can be spent as credit.

### Posting table (complete)

`Dr` = positive entry, `Cr` = negative entry. Every row is one journal transaction with
the given deterministic `idempotency_key`.

| # | Business event | Dr | Cr | Idempotency key |
|---|---|---|---|---|
| P1 | Commission created | `platform:commission_expense` | `user:pending` | `commission:{id}:create` |
| P2 | Commission confirmed | `user:pending` | `user:available` + `user:credit_only` split by `reward_split` (largest remainder) | `commission:{id}:confirm` |
| P3 | Pending commission cancelled / partially reduced | `user:pending` | `platform:commission_expense` | `commission:{id}:pending-reduce:{source_ref}` |
| P4 | Available commission reversed | `user:available` / `user:credit_only` per ADR 0008 | `platform:commission_expense` | `commission:{id}:reverse:{source_ref}` |
| P5 | Reversal reinstated (chargeback won) | `platform:commission_expense` | accounts debited by the matching P4 | `commission:{id}:reinstate:{source_ref}` |
| P6 | Credit reserved | `user:credit_only` first, then `user:available` | `user:reserved` | `reservation:{id}:reserve` |
| P7 | Credit captured (full or partial) | `user:reserved` | `platform:credit_redeemed:{product}` | `reservation:{id}:capture` |
| P8 | Credit released / expired / capture remainder | `user:reserved` | source accounts recorded at P6, `available` share returned first | `reservation:{id}:release` |
| P9 | Late capture (ADR 0011) | `user:credit_only` up to its positive balance, rest `user:available` (may go negative) | `platform:credit_redeemed:{product}` | `reservation:{id}:late-capture:{payment_ref}` |
| P10 | Credit refunded to user (§12) | `platform:credit_redeemed:{product}` | source accounts of the original capture, pro rata | `credit-refund:{product_id}:{idempotency_key}` |
| P11 | Withdrawal requested | `user:available` | `user:payout_hold` | `payout:{id}:request` |
| P12 | Withdrawal paid | `user:payout_hold` (gross) | `platform:payout_clearing` (net) + `platform:tax_withholding_payable` (tax) | `payout:{id}:paid` |
| P13 | Withdrawal rejected / cancelled / failed before payment | `user:payout_hold` | `user:available` | `payout:{id}:return-hold` |
| P14 | Paid withdrawal returned by provider | `platform:payout_clearing` + `platform:tax_withholding_payable` | `user:available` | `payout:{id}:returned` |
| P15 | Negative balance written off | `platform:writeoff` | `user:available` or `user:credit_only` (to zero) | `writeoff:{id}` |
| P16 | Manual adjustment (bonus / clawback) | `platform:commission_expense` ↔ user account | | `adjustment:{id}` |

Notes:
- **Netting (§10.4)** needs no special posting: P2 credits `user:available`, which
  offsets a negative balance automatically. Credit-only earnings do not net against a
  negative `available` (setting `ledger.net_credit_only_against_negative`, default
  `false`).
- **Chargebacks** use P3/P4 with `source_ref = chargeback:{chargeback_id}`, and P5 if
  the chargeback is won (ADR 0010).
- `platform:payout_clearing` is not cleared inside the platform in v1. Finance
  reconciles it against provider/bank statements using the payout CSV export.
- P15 and P16 are admin actions: audited, maker-checker above
  `finance.dual_approval_threshold`.

## Consequences

- Every money movement in the spec has exactly one posting rule and one idempotency key
  pattern; replaying any business operation is a no-op at the ledger.
- Property tests (I1, I3, I5) generate sequences over P1–P16.
