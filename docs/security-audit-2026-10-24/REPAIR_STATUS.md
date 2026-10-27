# Security repair batch 1 — 24 October 2026

Scope: password-reset isolation and the reported frontend dependency advisories. Changes apply to the shared generator and the current `payments-app` and `razorpay-app` demos. Historical generated projects and earlier evidence snapshots have not been silently rewritten.

## Implemented

- **SEC-02:** invalid recovery attempts now consume a persistent per-IP allowance (40 per 15-minute window), not an empty shared account bucket. After token validation, a separate per-user allowance applies. Reset quotas have no site-wide shared bucket. Invalid tokens do not consume another account's allowance. Existing token expiry, single use, password hashing and session revocation remain enforced.
- Added a regression that exhausts one IP's allowance, recreates the app/session to check persistence, successfully resets another user's password from another IP, checks sign-in, rejects token reuse and checks allowance expiry. This is a new post-fix assertion; the original vulnerability reproduction and its evidence are preserved.
- **SEC-01:** pinned Vite 6.4.5 and React plugin 4.7.0 in the reusable generator, model-output example, both demo manifests and offline runtime recipe. Updated both demo lockfiles and installed dependencies. This version pair supports the laptop's existing Node 18 installation; this repair does not upgrade or certify the security/support status of Node itself.
- Refreshed both installed offline Docker runtime images. Vite 6 bundles its configuration into `node_modules/.vite-temp`; because sandbox dependencies are read-only, that specific path now points to the existing `/tmp` tmpfs. No source write access, network access, extra capability or privilege was granted to generated-code tests.

## Verification

- Both demo production builds passed using Vite 6.4.5.
- Both demo npm audits returned **zero reported vulnerabilities**. This is an advisory scan result, not a guarantee of security. Raw results: `repairs/payments-app-npm-audit.json` and `repairs/razorpay-app-npm-audit.json`.
- Identity suite: **11 passed**, including the new cross-user reset regression and restart/throttle checks. Evidence: `repairs/platform-results.json`.
- Razorpay synthetic controls: **14 passed**; browser journey: **1 passed**. Evidence: `repairs/razorpay-app-results.json`. This covers mocked Checkout, account/cart/order behavior, keyboard interaction, desktop/mobile overflow checks and customer denial of administrator actions. Real provider integration remains unverified.
- Offline simulation results are recorded separately in `repairs/payments-app-results.json`.
- The initial browser test exposed Vite's new temporary-config write location. Its failure is preserved in `repairs/razorpay-app-before-sandbox-fix.json`; the compatibility fix allowed the unchanged browser assertions to pass.
- Host identity-test collection was blocked by Windows Application Control loading SQLAlchemy's compiled extension. Tests were completed in the isolated Linux runtime; Windows security policy was not changed. This does not establish that the laptop's host Python environment is healthy.

## Activation and remaining work

Restart any already-running demo backend and frontend to load the updated files and dependencies. A laptop restart or database reset is not required for these repairs. No real customer data, passwords, payment keys or database roles were changed.

The earlier generated-build verification digests belong to their old source snapshots. This targeted regression evidence does not silently promote a newly modified app to fully VERIFIED or production-ready.

Still open: SEC-03 least-privilege database roles; SEC-04 durable fast webhook intake; SEC-05 browser/production headers; SEC-06 Python installer maintenance; actual provider verification and the audit's remaining scan/deployment work. Existing shared thresholds on other auth endpoints and proxy/NAT rate-limit behavior also need review; the fix here is specifically recovery isolation, not a complete denial-of-service defense.

Next batch: separate database migration/runtime privileges, then implement durable webhook processing with slow-provider and restart tests. Keep live payments disabled.
