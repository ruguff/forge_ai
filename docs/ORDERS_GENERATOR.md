# Reviewed cart and unpaid-order generation

ProjectForge's `ORDERS` strategy composes the PostgreSQL catalogue and reviewed
customer identity modules with a fixed cart/order runtime. The language model can
select and configure the module, but does not generate the security-sensitive
checkout, pricing or stock mutation code.

## Supported workflow

- A signed-in customer edits a cart containing up to 20 active SKUs. Cart contents
  belong to the server-side account; editing requires the expected cart version.
- The server prices from the current variant records in integer minor units. The
  `OrderContract` must supply tax basis points, shipping in minor units, discount
  basis points, reservation duration and a human-readable policy label. These are
  store configuration values, not tax or legal advice. Tax is rounded half-up on
  discounted merchandise, discounts round down, and configured shipping is added
  afterward. The quote includes currency and a server-computed hash.
- Checkout requires an address owned by the customer and a fresh cart version and
  quote hash. A unique per-customer idempotency key makes a retry return the same
  order. A reused key with a different request is rejected.
- Checkout atomically snapshots the address, policy, product name, SKU, variant,
  quantity, unit price and line total. It reserves inventory by decrementing the
  available quantity. It creates an `awaiting_payment` order and never claims a
  payment or fulfillment succeeded.
- The customer can inspect order history and cancel a pending order. Cancellation
  and expiry restore the reserved quantities once. Reservation expiry runs at
  startup, on cart/order requests, and in a 30-second background sweep.
- Administrators can inspect the latest 100 orders. Pagination and order
  fulfillment transitions are outside this phase.

## Database and migration

The module appends checksum-checked migration `0003` after catalogue migration
`0001` and identity migration `0002`. It creates `carts`, `cart_items`, `orders`
and `order_items`, with foreign keys, quantity/total/state checks, and a unique
`(user_id, idempotency_key)` constraint. Store writes share a Postgres transaction
advisory lock so checkout cannot race a stock update or another checkout. This
conservative global lock is intended for a small single store, not high traffic.

## Out of scope

No payment is collected. There is no payment simulator, provider adapter, refund,
fulfillment or live credential support in this phase. No raw card information is
requested or stored. Payments and refunds belong to later phases. Security/load
scans and production deployment are not certified by these tests.

## Verification

From the repository's `backend` directory, run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe verify_orders_generator.py
```

The generated-app verifier needs Docker Desktop running with the prebuilt
`projectforge-relational-runtime:local` image. The sandbox has no network access,
uses an ephemeral PostgreSQL database, and launches Chromium for the UI journey.
It verifies generated TypeScript/Vite output, declared catalogue behavior,
customer registration and address entry, checkout/cancellation through the
rendered UI, server-authoritative totals, snapshots, idempotency, owner/admin
access, stale quotes, reservation expiry, a concurrent last-unit checkout, and
order persistence across backend-process restarts. The visual pass checks desktop
and mobile page overflow and records screenshots; it is a targeted review, not an
accessibility certification.

Evidence is written under `docs/ecommerce-evidence/` including
`orders-verification.json`, `orders-build-spec.json`, and the generated source at
`orders-app/`. Sample tax and shipping values in that fixture are synthetic test
values only and must not be reused as business policy.
