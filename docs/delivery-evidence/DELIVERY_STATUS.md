# Manual delivery status increment

Completed 27 October 2026. Scope: administrator-managed Not packed -> Packed ->
Shipped -> Delivered, then stop. These remain demo records, not courier evidence.

## Use the feature

1. Restart the already configured demo backend and frontend. Keep the backend's
   existing DATABASE_URL environment. Startup applies additive migration
   0005_delivery; `python migrate.py` is also supported. Do not reset the database.
2. Sign in as an existing administrator and open http://127.0.0.1:3001/admin/orders.
3. For an eligible settled demo order, click Mark order #... as packed, then
   shipped, then delivered. Customers see the saved status at /orders.
4. Unpaid, cancelled, expired and refunded orders cannot start delivery. Active
   refunds also block progression. Refund initiation after packing is rejected
   until a separate returns workflow is implemented.

Applies to docs/ecommerce-evidence/payments-app and razorpay-app and future
payment-enabled generation. No credentials, persistent demo records or previous
project versions were changed during verification. Restart is needed to activate.

## Implementation

- fulfillment_runtime.py provides authenticated administrator-only mutation,
  strict input, expected-status checks, one-step progression, idempotent retries,
  transactional serialization, audit records, and persistent delivery state.
- order_fulfillment is separate from financial order state. It records order ID,
  status, administrator ID and timestamp; foreign keys and a status check apply.
- Existing customer/admin order endpoints include delivery state; existing
  ownership enforcement remains. No separate public order lookup was added.
- Fulfillment.tsx shows status and only the valid next action. Refund controls are
  hidden after packing and rejected server-side. Financial and stock values are
  not changed by delivery updates. No automatic physical-return assumption.

## Verified results

| Check | Result | Evidence |
|---|---|---|
| Simulator financial regressions and delivery controls | 13 passed | payments-app-results.json |
| Synthetic Razorpay regressions and delivery controls | 15 passed | razorpay-app-results.json |
| Browser admin transitions, refresh, customer read-only view, mobile overflow | 1 passed | payments-app-results.json |
| Both frontend production builds | Passed | Both application result files |
| Unpaid, simulator and provider generator contracts | 29 passed | generator-results.json |

Screenshots: desktop.png and mobile.png. Reviewed for readable labels and no
horizontal overflow. Browser test exercises the actual backend and frontend;
Razorpay checks use a fake provider, never actual payment credentials.

## Test corrections and remaining scope

Acceptance contract v2 updates migration lists to explicitly include 0005_delivery
and source counts from 44 to 46 / 46 to 48, checking both new files exist. Previous
migration preservation checks, ownership and financial assertions remain intact.
The first delivery restart test used TestClient's non-loopback default and was
correctly rejected by local-only middleware. It now uses an explicit loopback
client, matching all other demo checks. First-run failures are retained in the
*-first-run.json evidence. No assertions were relaxed to ignore a functional error.

Generator checks initially lacked template assets and pydantic-settings in their
disposable test environment. Added source templates and already installed pure-
Python dependencies to that test copy; no Windows policy or package downloads.

No courier integration, tracking numbers, notifications, returns workflow,
production deployment or real provider verification was performed. Existing
security-audit findings outside this increment are still open. The prior Word
report has not been edited as part of this implementation request.
