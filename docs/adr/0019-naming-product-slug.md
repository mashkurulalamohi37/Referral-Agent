# 0019. Products are addressed by `slug`, not `code`

- Status: Accepted
- Date: 2026-10-08
- Blocks phase: 2

## Context

"Code" already means referral code everywhere (`/r/{code}`, `/public/codes/{code}`).
§18 uses `GET /v1/public/products/{code}/theme`, and §7.1 uses `?product=healora`.

## Decision

- Products have an immutable `slug` (`^[a-z][a-z0-9-]{1,31}$`, e.g. `healora`,
  `pulsepos`).
- Public theme endpoint: `GET /v1/public/products/{slug}/theme`.
- Query parameter on the redirect stays `product` and takes a slug.

## Consequences

- No overloaded term in URLs, schemas or the error registry.
