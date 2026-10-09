# Inbound Event Contract

Machine-readable schemas: [`events/`](events/) (JSON Schema 2020-12). The envelope
[`events/envelope.schema.json`](events/envelope.schema.json) dispatches on `event_type`
to the per-type `data` schema. Examples in `events/examples/valid` and
`events/examples/invalid` are checked by `python tools/check_contracts.py`.

## Transport (§8.1)

```text
POST /v1/events
Authorization: Bearer <key_id>.<secret>
X-Signature-Timestamp: <unix seconds>
X-Signature: v1=<hex HMAC-SHA256(signing_secret, timestamp + "." + raw_body)>
Content-Type: application/json
```

- Signature is computed over the **exact raw bytes** sent. Do not re-serialize.
- Timestamp must be within ±300 s of server time.
- `202 Accepted` with `{platform_event_id, state}` once persisted. Duplicate delivery of
  the same `event_id` and body returns `200` with the original id.

## Event types (v1)

| `event_type` | Ordering key resolution (ADR 0012) | Effect |
|---|---|---|
| `user.registered` | `external_user_id` | Upsert product account, hash signals (ADR 0015) |
| `subscription.created` / `.updated` | `external_user_id` | Upsert subscription |
| `subscription.cancelled` / `.expired` | from subscription | Stop future renewal commissions |
| `payment.succeeded` | `external_user_id` | Record payment, capture credit reservation, create commission if referred |
| `payment.failed` | from payment if known | Fact only, or full-refund treatment if previously succeeded (ADR 0010) |
| `payment.refunded` | from payment | Cumulative proportional reversal (ADR 0009) |
| `payment.chargeback` | from payment | Full reversal + risk signal (ADR 0010) |
| `payment.chargeback_resolved` | from payment | `won` reinstates (ADR 0010) |

Changes from spec §8.3, all from ADRs: `chargeback_id` added to `payment.chargeback`;
new `payment.chargeback_resolved`; optional `external_user_id` on refund, chargeback,
cancellation and failure events; inbound timestamps must be UTC.

## Validation beyond JSON Schema

Checked by the platform after schema validation:

- `amount_net_paid = amount_gross − discount_amount − tax_amount − credit_applied_amount`
  → `AMOUNT_INCONSISTENT`.
- `currency` enabled (v1: `BDT`) → `CURRENCY_NOT_ENABLED`.
- `plan_code` known for the product; unknown plans are auto-created as `status=UNREVIEWED`
  so payments are never dropped, and an admin alert is raised.
- Business keys unique per product: same `payment_id` with a different body under a new
  `event_id` → `BUSINESS_KEY_CONFLICT`; identical content → processed as a duplicate
  (no effect).

## Processing states (§8.4, ADR 0006)

`RECEIVED → PROCESSING → PROCESSED | IGNORED | FAILED (retrying) | WAITING_DEPENDENCY → … | DEAD_LETTER`

- `WAITING_DEPENDENCY`: retried with exponential backoff (1 min doubling, cap 1 h) for up
  to 72 h, then `DEAD_LETTER` + alert.
- `FAILED`: unexpected error; retried 10 times with backoff, then `DEAD_LETTER`.
- Replay (admin) moves `DEAD_LETTER`/`FAILED` back to `RECEIVED`. Effects are idempotent
  via business keys and ledger idempotency keys.

## Outbound webhooks (§8.5)

Schemas in [`events/outbound/`](events/outbound/). Same signature scheme with the
product's outbound signing secret. Retries with exponential backoff for 24 h, then dead
letter.
