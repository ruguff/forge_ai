# Phase 7 — Razorpay test adapter

Updated 2026-10-23. Live payment keys are rejected. This phase implements local code
and synthetic contract verification; a real Razorpay test account is still required
to establish provider integration. Do not interpret mocked success as bank/provider
evidence or production readiness.

## Generation and source

The reviewed `RAZORPAY_TEST` strategy builds on `ORDERS`, `IDENTITY` and `CATALOGUE`.
It generates 46 files in the verification fixture:
`D:\capstone_project\docs\ecommerce-evidence\razorpay-app`.
Generated `backend/app/razorpay_runtime.py` contains payment state and authorization;
`razorpay_client.py` contains the fixed HTTPS REST boundary. `frontend/src/RazorpayCheckout.tsx`
loads official provider Checkout only when requested. No app form collects card data.
The underlying platform modules are in `backend/app/execution/agent/`.

BuildSpec requires `razorpay_test_contract` with version 1, mode `razorpay_test`,
currency `INR`, refunds `admin_full_only`, plus existing catalogue/identity/order contracts.
PostgreSQL and INR are required. Simulator and provider contracts cannot be combined.
No secret fields are accepted in the contract. Compiler sections keep the existing
2048-token output bound; the reviewed manifest permits at most 48 files.
No larger local model is required. The fixture is compiled from a prepared typed spec;
it does not prove a new six-agent Nemotron planning run.

## Data and state

Migration `0004_razorpay_test` extends phase-5 `0003` transactionally and adds:

| Table | Purpose and constraints |
|---|---|
| razorpay_bindings | One provider intent per local order; unique receipt/provider order/payment IDs; account, integer amount, INR currency, state, stock-consumption flag, timestamps |
| razorpay_refunds | Administrator and order references; stable client/provider retry keys; unique provider refund ID; amount, payment ID, state; at most one creating/pending/processed refund per order |
| razorpay_events | Unique event ID, body digest, event kind, processing timestamp; no raw card/webhook payload |

Use a fresh provider database or a backed-up phase-5 ORDERS database. The simulator's
`0004` is a separate migration branch: it cannot silently become a provider database.
Old order-only code rejects the upgraded schema. Existing NoteKeeper, Task Manager
and previous demo folders are not migrated by the verifier.

Checkout records an intent before sending an API request. The server copies amount
and currency from the saved order, creates the provider order, and returns its public
Checkout settings. After a lost create response, recovery searches the saved receipt;
it never blindly creates another order. An absent match remains uncertain for review.

The callback signature alone is insufficient. The backend fetches current order and
payment evidence and matches IDs, account binding, amount, currency and captured state.
An authorized payment is not paid. Duplicate callbacks cannot consume stock twice.
Late captures after cancellation/expiry become `late_capture`; released inventory is
not reclaimed. Fulfillment remains disabled and administrators must arrange a refund.
Dashboard-issued refunds become `review` instead of silently restoring inventory.

Webhook HMAC covers the exact raw body; account and event IDs are validated. Stored
event IDs deduplicate redelivery. Supported events trigger current provider reads,
so delayed failed/authorized notifications cannot reverse captured/refunded outcomes.
Unknown orders/refunds return a retryable error rather than inventing bindings.
Secrets and unneeded payment response fields are never logged or persisted by this module.

Only administrators may request a full test refund. A persisted provider idempotency
key and unchanged payload are reused after uncertain responses. A definite failed
refund permits a new request. Processed refunds restore stock once, under the explicit
policy that fulfillment is disabled. An administrator can use **Request or retry full
test refund** to recover a `creating` request even after losing browser session storage.
This uses `/api/admin/razorpay/orders/{id}/retry-refund` and the server's original key.

## Local setup and verification

No account or real credentials are needed for the independent verification suite.
Start Docker Desktop and ensure `projectforge-relational-runtime:local` exists, then:

```powershell
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe verify_razorpay_generator.py
..\.venv\Scripts\python.exe -m pytest tests -q
```

The verifier uses a PostgreSQL sandbox with network disabled, limited CPU/memory,
unprivileged execution and a read-only source mount. Synthetic provider keys/responses
exist only in platform-owned tests. Mock Checkout JavaScript is intercepted by Playwright;
it is never shipped in the generated store. Production credentials are not passed through.

Evidence lives in `docs/ecommerce-evidence/razorpay-verification.json`, the generated
`.projectforge/*_results.json`, and desktop/mobile screenshots when the visual gate passes.
The report separates local functional checks, targeted security/layout checks, performance,
and provider integration. A `RAZORPAY_TEST` generated build remains `REQUIRES_HUMAN` with
`razorpay_provider_integration=UNVERIFIED`, even when all local checks pass. That is an
intentional evidence boundary, not a request to repeat the six-agent planning stage.

## Later: connect a real test account

Configure privately in the generated backend process environment, never in frontend
environment files, prompts, BuildSpec, shared reports or committed source:

| Variable | Required value |
|---|---|
| RAZORPAY_TEST_ENABLED | `1` |
| RAZORPAY_TEST_KEY_ID | Your `rzp_test_…` public key ID |
| RAZORPAY_TEST_KEY_SECRET | Matching test key secret |
| RAZORPAY_TEST_WEBHOOK_SECRET | Separate strong webhook secret, at least 16 characters |
| RAZORPAY_TEST_ACCOUNT_ID | Your `acc_…` account ID |

The generated README contains the database, seed, administrator and app startup steps.
Configure test automatic capture in the provider account. Visit `/orders` as a customer
and `/admin/orders` as an administrator. **Refresh provider status** reconciles a saved
order. From the generated backend folder, `python reconcile_payment.py ORDER_ID` provides
explicit operator reconciliation. No scheduled reconciliation worker is implemented.

Real Checkout/API calls require internet. Provider webhooks require an explicitly
approved reachable HTTPS staging endpoint; localhost alone cannot receive them. No tunnel
or public deployment is opened by this implementation. Configure `/api/razorpay/webhook`
for payment.authorized, payment.captured, payment.failed, order.paid, refund.created,
refund.processed and refund.failed events. Retain old-secret validation during a rotation
plan; automatic multi-secret rotation is not implemented here.

Before recording real integration evidence, test success and failure, checkout dismissal,
an authorized-but-not-captured attempt, signed webhook delivery/redelivery, refresh after
lost callback, invalid signatures, full refund and restart persistence. Record sanitized
IDs/statuses and timestamps. Never export credentials or raw card payloads. The automatic
local generator currently cannot promote this external evidence to VERIFIED; a reviewed
provider-evidence workflow remains necessary.

## Targeted threat model and release limits

| Threat | Implemented control | Evidence category / remaining work |
|---|---|---|
| Customer changes prices or claims payment | Server amount/currency/ID matching and captured-provider reads | Local negative contract tests; real test-account evidence pending |
| Forged or replayed callbacks/webhooks | HMAC, exact raw body, account match, persistent event deduplication | Synthetic signature/replay cases |
| Cross-customer access or unauthorized refunds | Session, CSRF/Origin, owner checks, administrator checks | Independent local negative cases |
| Lost responses or repeat refund clicks | Durable intents, unique constraints, advisory transaction lock, stable provider key | Lost-response/retry/concurrent cases |
| Delayed capture after inventory release | Explicit late_capture, no stock reclamation, admin refund | Local expiry/cancel cases |
| Secret leakage or external redirection | Server-only configuration, fixed HTTPS host, redirects denied, generic errors | Boundary unit tests; full secret/dependency scan still pending |
| Request/resource abuse | Existing body/session limits, 64KB webhook bound, per-action account/IP/global limits, response/timeout bounds | Targeted tests; load testing and public edge protection pending |

These controls map to applicable ASVS authentication, session management, access control,
input validation, cryptography, business logic and API topics; they are not certification
or full ASVS coverage. Phase 8 must assess deployment, dependencies, secret scanning,
accessibility, load/resource behavior and operational recovery separately. No live payments,
fulfillment, partial refunds, subscriptions, marketplace, scheduled reconciliation, webhook
secret rotation, or retention cleanup is delivered. Tax/shipping remain explicit demo
configuration, not legally authoritative policy.

## Official provider references

Reviewed 2026-10-22 and rechecked webhook/idempotency guidance 2026-10-23:

- [Standard Checkout and server signature verification](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/)
- [Create provider orders](https://razorpay.com/docs/api/orders/create/)
- [Fetch orders and receipt filtering](https://razorpay.com/docs/api/orders/fetch-all/)
- [Fetch payments for an order](https://razorpay.com/docs/api/orders/fetch-payments/)
- [Fetch a payment](https://razorpay.com/docs/api/payments/fetch-with-id/)
- [Raw-body webhook validation, duplicates and testing](https://razorpay.com/docs/webhooks/validate-test/)
- [Refund idempotency and retry semantics](https://razorpay.com/docs/api/refunds/normal-refunds-idempotent/)
- [Fetch refund state](https://razorpay.com/docs/api/refunds/fetch-with-id/)
