# Courier and tracking details — 27 October 2026

## Behavior

The admin order screen now has **Courier name** and **Tracking number** fields.
Saving requires both values (maximum 100 characters each). Leading/trailing spaces
are trimmed. Control characters, markup and unsupported tracking-number characters
are rejected. Courier names support Unicode letters; tracking numbers support
ASCII letters, numbers, spaces, dots, underscores, slashes and hyphens.

An administrator may save or correct these details on a paid order with no active
refund until delivery. After delivery the record is read-only. The existing manual
Packed → Shipped → Delivered flow remains available for orders without tracking.
Customers can read the details only through their own order history.

Saving does not mark an order shipped, change payment status, or modify inventory.
Values are entered by the store; there is no courier booking, external tracking
lookup, notification, carrier API or automatic delivery update.

## Implementation

- Shared runtime: `backend/app/execution/agent/fulfillment_runtime.py`.
- Shared React component: `backend/app/execution/agent/order_templates/Fulfillment.tsx`.
- Simulator and Razorpay test generators both include the feature and a version-2
  delivery UI contract. Both checked-in applications under
  `docs/ecommerce-evidence/{payments-app,razorpay-app}` have been updated.
- `POST /api/admin/orders/{order_id}/shipping-details` requires an admin session,
  valid origin/CSRF token, and `expected_version` (0 for first entry).
- A transaction lock and version check prevent competing edits from overwriting
  one another. An exact retry of the most recent update has no extra effect.
- Audit records identify the actor, order, action and time. Actor IDs are not
  exposed in customer shipping data.
- Additive migration `0006_tracking` creates `order_shipping_details` with order
  and user foreign keys, field-length constraints and a positive version number.
  Migration `0005_delivery` and earlier checksums remain unchanged.

## Activation

Restart the commerce demo backend using the same `DATABASE_URL` as before. Startup
applies the migration; `python migrate.py` may also be used explicitly. Do not
create a new database or delete the existing volume. Refresh the frontend.

For the simulator demo, open `http://127.0.0.1:3001/admin/orders`, sign in as an
administrator, and choose a paid, not-yet-delivered order without an active refund.
Enter both values and select **Save shipping details for order #…**. The customer
can see them at `http://127.0.0.1:3001/orders` after refreshing.

## Verification evidence

Reproduction commands from the repository root:

```powershell
.\.venv\Scripts\python.exe docs/run_tracking_checks.py
.\.venv\Scripts\python.exe docs/check_tracking_generator.py
```

The runners copy source into disposable, network-disabled Docker environments
using `projectforge-relational-runtime:local`. They use synthetic users, payments
and isolated PostgreSQL databases; they do not modify the user's demo database.

The final verification run passed 18 simulator/API cases, 15 synthetic provider
cases, 29 generator cases, two frontend builds and the tracking browser journey.
Tracking controls are included in the normal simulator verification gate; provider
controls include manual tracking and delivery. Results are recorded in
`payments-app-results.json`, `razorpay-app-results.json` and `generator-results.json`.

Coverage includes admin/customer/CSRF restrictions, input validation, stale edits,
concurrent edits, exact retries, audit counts, owner-only reads, restart persistence,
payment/refund/delivery restrictions and unchanged stock/totals. A pre-tracking
database-shape fixture verifies that the new migration preserves existing orders,
paid/packed state and previous migration checksums.

Browser checks save and correct tracking data, resolve an actual stale edit,
reload the page, advance delivery, check read-only delivered records, and confirm
customer visibility without edit controls. Desktop and mobile screenshots are
saved as `form_desktop.png`, `form_mobile.png`, `desktop.png`, `mobile.png` and
`customer.png`. The mobile check asserts no horizontal page overflow at 390px.

Schema assertion changes explicitly add the new migration revision; existing
financial, permission and delivery assertions were retained. The shared runtime
advertises its tracking schema version for the migration checks.

Provider cases use a synthetic gateway. They do not establish real Razorpay or
courier integration. Existing load/security release limitations still apply.
