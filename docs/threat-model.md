# Threat Model (v1)

Method: STRIDE per trust boundary, then abuse cases specific to referral programmes.
Baseline controls come from spec §5, §7, §8, §14, §15, §22.3 and OWASP ASVS L2.
Each threat lists its control and the test that proves it (§22.4). Owner: platform team;
revisit at Phase 14 hardening and whenever a trust boundary changes.

## Assets

| Asset | Why it matters |
|---|---|
| Ledger and balances | Direct financial loss |
| Payout details (bKash/Nagad/bank) | Fraud, PII |
| API client secrets, signing secrets | Forge events = mint commission |
| Attribution token key, JWT key, signal pepper | Forge attribution / sessions / de-anonymise signals |
| Referred-user identity per product | Healora usage is health-sensitive (§15) |
| Admin accounts | Full control over money |
| Audit log | Accountability; must be tamper-evident |

## Trust boundaries

1. Internet → `ref.example.com/r/` and public endpoints (anonymous).
2. Product backends → service API (API client credentials + HMAC).
3. Browser → portal/admin APIs (JWT sessions).
4. API/worker → Postgres/Redis (internal network).
5. Platform → product webhook URLs (outbound).
6. Operators → CLI / admin panel (privileged humans).

## STRIDE

| # | Boundary | Threat | Control | Test |
|---|---|---|---|---|
| S1 | 2 | Forged events from an attacker to mint commissions | Bearer secret (hashed at rest) **and** HMAC over raw body with a separate signing secret; product from credential only | security: missing/invalid/revoked key, bad signature |
| S2 | 2 | Replay of a captured, validly signed event | ±300 s timestamp window; `(product_id, event_id)` unique; business-key uniques | security: stale timestamp; concurrency: 20 duplicates → 1 commission |
| S3 | 3 | Session theft | 15-min access token in memory; refresh in `HttpOnly; Secure; SameSite=Lax` cookie; rotation with reuse detection revokes family; CSP | security: refresh-token reuse, expired JWT |
| S4 | 6 | Admin account takeover | TOTP required for admin roles; separate admin hostname; optional IP allowlist; login rate limit | security: admin login without TOTP |
| S5 | 1 | SSO handoff token theft | 60 s TTL, single use, hashed at rest, bound to product account; delivered via redirect over TLS | security: reuse of handoff token |
| T1 | 4 | Tampering with ledger history | Insert-only triggers (I2); balances derivable (I3) + nightly reconciliation alert; DB role for app cannot `ALTER`/`DISABLE TRIGGER` | invariant: UPDATE/DELETE on ledger raises; I3 property test |
| T2 | 2 | Product A acting on product B's accounts | Product resolved from credential; all queries scoped by `product_id`; cross-product resources return 404 | security: cross-product access |
| T3 | 1 | Attribution token tampering (change code/campaign/expiry) | JWS (HS256 with `ATTRIBUTION_TOKEN_KEY`, `kid` for rotation); `product` claim must equal the calling product | unit: tampered token, wrong product |
| T4 | 3 | Mass assignment / unknown fields (incl. health data) | Pydantic `extra="forbid"` on every input model (I9) | contract: invalid examples; unit per schema |
| R1 | 6 | Admin denies a financial action | Audit log with actor, before/after, IP, request ID; insert-only; maker-checker above threshold | E2E: rule edit → audit entry |
| I1 | 1 | Referral code enumeration to harvest referrer names | `/public/codes` returns only `valid` + display name; per-IP token bucket; `/r/` gives no distinguishable signal; codes ≥ 4 chars of 29-symbol alphabet with random suffix | security: enumeration rate limit |
| I2 | 3 | Referrer learns that a contact uses Healora | Per-product visibility; Healora `NONE` (ADR 0016); notification copy omits product for sensitive products | unit: visibility masking per mode |
| I3 | all | Secrets/PII in logs | Logging filter redacts keys by name and by pattern (tokens, phone, email, card-like numbers); unit-tested | unit: log redaction |
| I4 | 4 | DB dump exposes payout details or signals | Payout details AES-GCM with separate key; signals stored only as HMAC with pepper; API secrets hashed | unit: no raw signal persisted |
| I5 | 1 | Open redirect via `/r/` | Redirect target only from product registry `signup_url`; query string never used as target | security: open-redirect attempt |
| D1 | 1, 2 | Flooding `/r/` or `/v1/events` | Nginx limits + Redis token buckets per IP / per client; events endpoint does minimal work before 202 | load test (Phase 14) |
| D2 | 2 | Poison event blocks a customer's ordering key | Bounded retries, `DEAD_LETTER` releases the key; dead-letter alert | integration: dead letter + replay |
| E1 | 3 | Privilege escalation via role checks scattered in code | Central permission map; deny by default; tests enumerate every admin route × role | security: role matrix test |
| E2 | 6 | Single finance admin pays out to themselves | Maker-checker with `approved_by <> requested_by` CHECK; payouts to admins' own accounts require SUPER_ADMIN | unit: same-actor approval rejected |
| E3 | 5 | SSRF through product webhook URL | Webhook URLs set by admins only; HTTPS only; resolved IP must not be private/link-local; no redirects followed | unit: private IP rejected |

## Referral-programme abuse cases

| # | Abuse | Control |
|---|---|---|
| A1 | Self-referral with a second account | Hard block on same user / linked account / matching hashed email or phone (§7.3); risk rules on shared device, IP prefix, payment fingerprint (§14.2) |
| A2 | Cookie stuffing / forced clicks to steal attribution | Typed code wins over token (Q7); token alone needs a real click (`click_id` exists, not expired); click → signup timing risk rule |
| A3 | Re-attributing existing customers | New accounts only: grace window, no prior payment, click-before-signup (ADR 0013); admin-only otherwise, audited |
| A4 | Pay → earn → refund → withdraw | Confirmation period (≥ refund window, Q2); reversal after confirmation goes negative and blocks withdrawal (§10.4); high-refund-rate risk rule |
| A5 | Minimum payment then cancel, repeatedly | `min_net_paid_minor`; risk rule on min-pay-then-cancel pattern |
| A6 | Double-spend credit with parallel reservations | Row locks on accounts; concurrency test with 20 parallel reservations (I5) |
| A7 | Product (or compromised product key) resends a payment under a new `event_id` | Business key `(product_id, payment_id)` unique; `BUSINESS_KEY_CONFLICT` alert |
| A8 | Insider edits a rule to pay a friend | Rule versioning, audit, maker-checker on rule activation above a configured rate, rule simulator visibility |
| A9 | Vanity code impersonating brand/staff | Vanity codes need approval; reserved-word and profanity list |

## Residual risks (accepted for v1)

- A compromised product backend can still send fully valid events for its own product.
  Mitigations are detection (reconciliation ADR 0017, risk velocity rules, per-product
  commission dashboards), not prevention.
- Hashed email/phone signals are linkable across products by design (needed for
  self-referral detection). The pepper is a single secret; its rotation requires
  re-hashing from fresh signals, so old hashes stop matching (documented in runbooks).
- Manual payout provider relies on finance staff entering correct references; mitigated
  by maker-checker and CSV reconciliation.
