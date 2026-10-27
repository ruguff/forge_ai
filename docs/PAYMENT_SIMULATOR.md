# Offline payment simulator — Phase 6

The `PAYMENT_SIMULATOR` strategy composes reviewed catalogue, identity and order
modules. The model selects/configures typed contracts; it does not invent payment
or stock mutation code. The generated app never calls a bank or payment gateway.
Simulation does not count as verified Razorpay integration or production readiness.

## State and inventory rules

| Action | Simulation state | Order state | Inventory effect |
|---|---|---|---|
| Create order | Not started | awaiting_payment | Reserve available stock |
| Start simulator | pending | awaiting_payment | None |
| Simulate success | succeeded | simulated_paid | Keep reserved units consumed |
| Simulate failure | failed | cancelled | Restore once |
| Simulate cancellation | cancelled | cancelled | Restore once |
| Cancel pending order | cancelled, if started | cancelled | Restore once |
| Reservation expires | expired, if started | expired | Restore once |
| Admin requests full simulated refund | Payment succeeded; refund pending | simulated_paid | None |
| Simulate refund failure | Payment succeeded; refund failed | simulated_paid | None; admin can retry |
| Simulate refund success | refunded | simulated_refunded | Restore once |

No partial payments/refunds, actual returns, fulfillment, subscriptions, webhooks or
provider reconciliation exist in this phase. Stock restoration after a refund is
valid here specifically because this app cannot ship/fulfill an order. A future
fulfillment module must change that policy explicitly.

One payment attempt exists per order. A failed/cancelled order is terminal; create a
new order to try again. Duplicated identical mutation keys return current persisted
state without repeating effects. Key reuse with a different request fails. A late
or contradictory terminal outcome fails. Success received after expiry is rejected.
The browser stores retry request metadata, not credentials, in sessionStorage;
refresh or retry an ambiguous request before discarding it. Server authority remains
mandatory even if the local request metadata is edited.

## Contracts and generation

`PaymentSimulationContract` accepts only version 1, mode `offline_simulator` and
refunds `admin_full_only`. Unknown keys, live mode and API credentials are rejected.
PostgreSQL, session identity and an explicit OrderContract are required. Tax,
shipping, discounts and currency remain business configuration, not invented policy.
The reviewed manifest has 44 files. The compiler permits up to 48 unique files for
this strategy; all earlier strategy bounds and 2048-token local section limits stay.
The model is never asked to output the reviewed runtime source.

Migration 0004 adds `simulated_payments`, `simulated_refunds`, `simulation_events`
and expands the order state constraint. It preserves migrations 0001–0003 and
existing orders. Foreign keys, unique order/payment associations, one active or
successful full refund, integer money, state checks and shared transaction locking
protect writes. Unknown schema histories and old code against migration 0004 fail
closed. Back up a real development database before applying any schema upgrade.
The tests use disposable isolated PostgreSQL; no existing saved project is upgraded.

## Security boundary and checks

- Customer mutations require session, Origin/CSRF and order ownership. Refund
  mutations also require an administrator role. Public signup cannot grant that role.
- Amount and currency are copied from the server order. Submitted outcome values
  must match; card fields, prices and unexpected fields are rejected.
- Persistent action rate limits: 30/account, 40/IP and 200/global per five-minute
  fixed window for each operation. Retries count toward these limits.
- Terminal transition, idempotency, payment/refund and stock writes share one
  transaction lock. Events and audit records contain no payment credentials.
- Paid simulations do not expire. Ordinary cancellation of settled orders fails.
- Runtime execution uses the existing offline, unprivileged, resource-limited
  Docker sandbox. No live credentials or public network access enter verification.

Applicable threats: cross-account access, forged totals, CSRF, duplicate/reordered
outcomes, concurrent outcomes, refund privilege escalation and repeated stock
restoration. These have targeted checks; this is not full OWASP ASVS conformance,
an independent penetration test, dependency/secret scan or load verification.
Event retention, pagination beyond the existing bound, partial refunds, real email,
high-throughput locking and operational deployment remain outside Phase 6.

## Verification and demonstration

From `D:\capstone_project\backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe verify_payments_generator.py
```

Docker Desktop must be running and `projectforge-relational-runtime:local` present.
The verifier writes `docs/ecommerce-evidence/payments-app`, a generated fixture
from a prepared typed spec. It does not prove a new live six-agent Nemotron run.
Backend, frontend build, frozen acceptance/browser contracts, identity, orders,
simulation API and simulation browser gates are mandatory and separately recorded.
Negative simulation results prevent VERIFIED even when backend pytest passes.
Provider integration stays NOT_IMPLEMENTED; performance stays UNVERIFIED.

To inspect the generated source:

```powershell
cd "D:\capstone_project\docs\ecommerce-evidence\payments-app"
code .
```

Use its README for the persistent development database, backend, frontend and
administrator setup. Startup applies the migration; it does not provide an admin
password. Visit `/account`, add an address, choose a product, open `/cart`, create
an unpaid order, then use its clearly labelled simulator controls. `/orders` shows
saved outcomes. An administrator uses `/admin/orders` for full simulated refunds.
All verification accounts, orders and database contents are synthetic and ephemeral.

Evidence: `payments-verification.json`, `payments-build-spec.json`,
`payments-regression-tests.log` and `payments-*.png` in `docs/ecommerce-evidence`.
The next phase is a separate Razorpay test adapter; live payments remain disabled.
