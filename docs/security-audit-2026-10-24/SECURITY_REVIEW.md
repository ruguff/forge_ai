# ProjectForge generated commerce security review

Date: 24 October 2026. Original audit evidence is retained below. Follow-up: SEC-02 reset throttling has been corrected and SEC-01 frontend dependency matches have been addressed for the two current demos and future generation. See [repair verification](REPAIR_STATUS.md) for the exact scope, tests and remaining work; the original reproduction results describe the pre-fix source.

## Scope and conclusion

Reviewed the local `docs/ecommerce-evidence/payments-app` offline simulator and `docs/ecommerce-evidence/razorpay-app` test-provider application, including shared identity, orders, payment code, frontend configuration, dependencies, and database setup. These are generated demo applications; this is not a certification of all ProjectForge outputs or an internet penetration test.

The store has meaningful authorization and payment safeguards, but should not be published with live payments in its current configuration. The most urgent work is updating vulnerable development dependencies, correcting shared password-reset throttling, separating database roles, and making webhook intake durable and fast.

Tests used copied source files, synthetic accounts and provider objects in a network-disabled, disposable PostgreSQL sandbox. No real customer database, Razorpay account, secret, charge, or refund was used. Docker Desktop was started for these tests. The actual demo database and application source were not changed.

## Findings

### SEC-01 — Vulnerable frontend development dependencies

**Priority: high remediation priority; confirmed advisory/version match, exploitation not attempted.**

The payments demo lockfile resolves Vite **5.4.21** and esbuild **0.21.5**. `npm audit --json --ignore-scripts` reported two affected packages: one high and one moderate, with multiple underlying advisories. This is a package count, not a count of independent exploitable attacks.

Evidence: `npm-audit.json`; `docs/ecommerce-evidence/payments-app/frontend/package-lock.json`. Both commerce frontends request Vite `^5.0.12`. The Razorpay demo has no checked lockfile, so its exact installed dependency tree was not established here.

Examples include Windows alternate-path file-access restrictions and development-server access issues. Some other advisories require particular editor configurations, non-Windows paths, or esbuild's own serve API. The presence of esbuild through Vite alone does not prove that its vulnerable serving API is exposed. The demos bind to loopback, reducing remote reachability; this does not make all development-server advisories irrelevant. These findings concern development/tooling exposure, not automatic proof that the compiled static website exposes source files.

Fix: select a currently patched, supported Vite/React-plugin/Node combination, update the generator dependency template and both demo lockfiles, then rerun build and browser tests. Do not blindly run `npm audit fix --force`. Do not publish the Vite development server as a production server.

Primary advisory: [Vite Windows deny-list bypass](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff). All returned advisory identifiers and affected ranges are retained in the audit JSON.

### SEC-02 — One visitor can exhaust password resets for everyone

**Severity: medium; reproduced. CWE-400 / shared throttling design.**

Location: `docs/ecommerce-evidence/razorpay-app/backend/app/identity_runtime.py:176` and `:332`; the payments demo and generator share this pattern.

The reset endpoint calls `limited(request, 'reset', limit=8)` without an account identifier. The limiter therefore uses the same `reset|account|` bucket for every visitor. Invalid tokens consume this shared bucket before token lookup. A different IP does not avoid the shared account bucket.

Evidence: eight invalid, syntactically valid reset submissions from synthetic client `127.0.0.2` returned HTTP 400; a different user's valid unused reset token from `127.0.0.1` then returned HTTP 429. The victim token remained unused. Lockout lasts until the current 900-second bucket ends, and can be repeated in later windows. No account compromise or password change was demonstrated.

Fix: use separate anonymous/IP abuse controls, then a scoped per-user limiter after safely validating the token. Never use an empty account identifier for a site-wide low quota. Review the shared IP/global thresholds on other authentication endpoints as well, particularly behind a reverse proxy or campus NAT. Test that an abusive client cannot block a valid unrelated user's recovery.

Evidence: `synthetic-results.json`, test `test_reset_shared_bucket_denies_a_different_victim`.

### SEC-03 — Application database connection uses the bootstrap superuser

**Severity: medium configuration risk; confirmed setup design, existing database privileges not queried.**

Location: `docs/ecommerce-evidence/payments-app/backend/compose.yaml:5` and `README.md:9–10`.

Compose initializes PostgreSQL with `POSTGRES_USER: projectforge`; the README connects the application as that same user. The official image creates this bootstrap user with superuser privileges on a new database volume. An application compromise would consequently have much greater database authority than necessary. This is not evidence of an SQL injection or a Windows host escape.

Fix: separate bootstrap, migration and runtime roles. Runtime should have only needed schema/table/sequence privileges and no superuser, role creation or database creation powers. Run migrations as a separate setup step. Verify privileges in a disposable installation and ensure normal store operations still work. Existing volumes retain their previous roles; changing the Compose variable alone does not repair them.

Source: [PostgreSQL official image — POSTGRES_USER](https://hub.docker.com/_/postgres).

### SEC-04 — Webhook acknowledgement waits for slow provider calls

**Severity: medium availability/reliability risk; reproduced with a synthetic provider.**

Location: `docs/ecommerce-evidence/razorpay-app/backend/app/razorpay_runtime.py:313–346`; `razorpay_client.py` uses an eight-second HTTP timeout.

Webhook processing reconciles remote provider state synchronously before recording the event and returning success. One artificial 5.2-second provider delay caused acknowledgement after **5.22 seconds**. Multiple provider calls can extend this further. Razorpay requires a 2xx acknowledgement within five seconds and retries failures; prolonged failures can disable the webhook. This can cause delayed financial status updates and repeated work. It did not bypass signature validation or produce a false successful payment in this test.

Fix: validate signature/account and basic schema, persist a deduplicated durable inbox record, then acknowledge promptly. A bounded worker should reconcile, retry with backoff and record failures. Retain idempotency, event/body consistency checks and out-of-order protection. Test worker restarts, duplicate delivery, slow upstream calls and reconciliation after outage.

Evidence: `synthetic-results.json`, test `test_webhook_ack_waits_for_slow_provider`. Provider contract: [Razorpay webhook response deadline](https://razorpay.com/docs/webhooks/setup-edit-payments/).

### SEC-05 — Storefront lacks explicit anti-framing / CSP deployment controls

**Severity: low confirmed configuration gap; impact conditional on deployment.**

The frontend `vite.config.ts` defines proxy/host configuration without response security headers; no CSP or frame restriction was found in the inspected frontend source/index. The backend's `identity_runtime.py:107–138` adds nosniff and no-referrer to API responses, but does not protect the separately served HTML document from framing.

This leaves a clickjacking hardening gap if no reverse proxy supplies those headers. SameSite=Lax cookies help against cross-site authenticated framing, so this is not a demonstrated account takeover. No hostile-frame browser exploit or production response-header test was performed.

Fix: configure security headers on the server that serves the actual HTML, including `Content-Security-Policy: frame-ancestors 'none'` where embedding is unnecessary. Develop and test a restrictive script/connect/frame policy that explicitly permits required Razorpay Checkout resources. Avoid breaking Checkout with an untested blanket CSP. Add HTTPS and suitable HSTS at the public deployment edge.

Source: [OWASP clickjacking defense guidance](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html).

### SEC-06 — Demo Python installer has advisory matches

**Priority: medium tooling maintenance; conditional installation-time exposure.**

The payments backend virtual environment contains pip **25.0.1**. Public PyPI per-version advisory metadata returned 12 records, representing six distinct CVE groups after alias deduplication, including archive/path handling during package installation. These are not 12 distinct website vulnerabilities. Several depend on malicious packages/indexes or older Python extraction behavior; no malicious package was installed or exploit attempted.

Evidence: `python-advisories.json`. Nineteen installed distribution versions were checked; only pip returned advisory records. This metadata lookup is narrower than a complete software-composition scan and does not establish that other packages are secure. It does not cover the container's Python packages or OS libraries.

Fix: upgrade pip to a current patched version compatible with the supported Python runtime, restrict package indexes, use reviewed pinned dependencies and hashes, and separately scan the verification container. PyPI metadata is recorded in the evidence rather than assuming every advisory is applicable to the host's Python version.

## Controls verified during this audit

Three new isolated checks completed: two intentionally reproduced the findings above, and one checked protective controls. A passing reproduction test means the vulnerability exists, not that it is fixed.

The existing synthetic provider suite was also rerun: **14 passed, 0 failed**. Evidence is `provider-controls.json`. Checks included:

- Customer order ownership and admin-only financial actions.
- CSRF rejection on protected mutation routes.
- Invalid signatures, mismatched account/amount/currency and non-captured payments.
- Duplicate and out-of-order webhook handling; concurrent callback/webhook application.
- Lost provider responses, stable refund keys, pending/processed refunds and replay.
- Late capture after cancellation/expiry without silently reclaiming released stock.
- Payment state persistence across a new backend process and rate-limit persistence across sessions.

These use a fake provider and do not verify the actual Razorpay account or live/test-provider networking. Tests emitted an existing Starlette/httpx deprecation warning; it is not itself a confirmed vulnerability.

Source review also found parameterized SQLAlchemy operations, server-calculated totals, hashed sessions/reset tokens, scrypt password hashing, HttpOnly cookies, strict request fields, ownership-qualified queries, bounded request bodies, and a five-pending-order limit. These are useful protections, not guarantees that every route and business case is secure.

## Remaining security work and boundaries

- No exhaustive automated SAST, entropy-based secret scan, container/OS vulnerability scan or deployed TLS/reverse-proxy review was completed. Actual credential values were not inspected.
- No sustained traffic/load attack, real provider request, email delivery test, Windows host attack, or test against the user's persistent demo database was performed.
- Inventory reservations expire and are capped at five per account, but multi-account stock-hoarding and repeated reserve/cancel abuse need explicit anti-automation/business policy and tests. This audit did not demonstrate overselling.
- The current local HTTP setting is deliberate for a loopback demo. Public deployment must use the HTTPS session configuration, trusted proxy/client-IP handling, ingress timeouts and request/concurrency limits. The application request-body cap alone does not prevent slow clients.
- Password recovery uses a local delivery option in development; production needs controlled delivery, token-file retention/permissions review, monitoring and an account-recovery threat assessment. Admin MFA and email verification remain hardening considerations.
- Browser XSS payload coverage, file/media-upload security if added, backup/restore access, audit retention/alerting, full ASVS mapping and actual provider integration remain unverified.
- The offline payment simulator intentionally lets the demo user choose an outcome. It must remain labelled and excluded from real financial fulfillment; simulation success is not a real payment.

## Recommended repair order and completion criteria

1. Correct reset throttling in the shared module and regenerate demos; the unrelated-victim test must then succeed rather than expect 429.
2. Upgrade and lock frontend dependencies and installation tools; review fresh advisories, build and inspect both storefronts.
3. Introduce least-privilege runtime database roles without weakening migrations or persistence tests.
4. Implement durable asynchronous webhook intake; assert acknowledgement inside the provider deadline even when upstream calls stall, with eventual verified state and safe replay.
5. Add and browser-test production response headers, proxy limits, HTTPS and monitoring; run the remaining scans and ASVS review before any live-payment approval.

Apply fixes to reusable generator modules as well as demos so regenerated websites do not reintroduce them. This report does not mark any of these repairs complete.
