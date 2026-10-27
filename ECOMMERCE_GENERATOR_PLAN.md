# E-commerce generator implementation ledger

## Customer shipment tracking — 27 October 2026 (verification in progress)

- Added an owner-only shipment API and customer tracking page, linked from orders.
- Timeline timestamps come from saved order/delivery events. Missing historical
  times and delivery estimates are not invented. No new migration is required.
- Pending: API authorization/state tests, both frontend builds, generator checks,
  browser refresh/copy/error checks and desktop/mobile inspection.

## Courier and tracking increment — 27 October 2026 (complete for manual tracking)

- Added manual courier name and tracking number to the shared delivery runtime,
  generator UI contract, and simulator/test-provider demo sources.
- Additive migration `0006_tracking` preserves `0005_delivery` and all earlier
  checksums. Admin edits use version checks, audit records, existing CSRF/session
  protection and the shared transaction lock. Customer reads retain order ownership.
- Both fields are required when saving; existing status transitions remain usable
  without tracking. Paid orders without active refunds can be edited until delivery.
- Passed: 18 simulator/API cases, 15 synthetic provider/API cases, 29 generator
  regression cases, both frontend builds, and one browser journey covering desktop
  and mobile layouts, stale-edit recovery, saved values and customer visibility.
- Upgrade/restart/concurrent-edit checks passed in disposable PostgreSQL databases.
  Desktop/mobile screenshots were inspected; the 390px browser check reports no
  horizontal overflow. Existing demo data was not used or changed by these tests.
- Simulator builds now run tracking controls through their normal payment gate;
  the provider gate includes courier/delivery coverage with synthetic responses.
- Evidence and activation steps: `docs/tracking-evidence/COURIER_TRACKING.md`.
- No courier service calls, dispatch booking or automatic carrier updates.

Updated 2026-10-23. This ledger distinguishes implementation from verified delivery.

## Initial repository audit (before upgrade)

- Platform: React/TypeScript frontend, FastAPI backend; SQLite JSON snapshots,
  history and replayable events in `backend/app/api/persistence.py`.
- Planning: six specialist agents, bounded structured-output harness and lint,
  followed by architecture and sectioned BuildSpec compilation. Local inference
  uses LM Studio. An interrupted run is marked INTERRUPTED; specialist reuse is
  not currently implemented.
- Generation: model coding plus a deterministic declarative CRUD compiler.
  The latter supports one entity and SQLite, not a commerce application.
  Existing NoteKeeper and Task Manager source/version directories must remain intact.
- BuildSpec has entities and textual relationships but the executable compiler
  rejects relational/multi-entity CRUD and PostgreSQL. Merely adding schema fields
  does not establish support.
- Execution: generated code runs in a restricted Docker sandbox with offline,
  preinstalled dependencies. Current image has no supported PostgreSQL service.
- Verification: backend pytest, frontend build, platform acceptance checks and
  browser journeys. `tests_passed` describes backend tests only. VERIFIED does not
  establish load/security/accessibility/provider coverage. Browser tests share
  database state; generated assertions are not a sufficient independent oracle.
- Current retry rebuilds source. Task graph is saved after generation rather than
  durably checkpointing every completed task. Old verification must never be reused.

## Phases and acceptance gates

| Phase | Scope | Required evidence | Status |
|---|---|---|---|
| 0 | Audit and baseline | Source audit; legacy regression tests | Complete: audit above; regression suite passes |
| 1 | Explicit recovery and UI contract | Interrupted build resumes; changed files/spec invalidate reuse; browser selectors use versioned contract | Complete for API recovery and opt-in CRUD contract; evidence below |
| 2 | Multi-entity generation and PostgreSQL | Related CRUD, migrations, FK/unique checks, restart persistence, legacy regressions | Complete for bounded related CRUD and initial migration; PostgreSQL gate passed 2026-10-21 |
| 3 | Catalogue and responsive design system | Categories, variants, images, search/filter; desktop/mobile inspection and keyboard checks | Complete for public read-only catalogue; final gate and visual review passed 2026-10-22 |
| 4 | Identity/permissions | Session, recovery, CSRF, rate-limit, role/ownership negative tests | Complete for reviewed accounts and catalogue administration; final gate passed 2026-10-22 |
| 5 | Cart/orders/inventory | Server prices, snapshots, idempotency, PostgreSQL restart/race gates, rendered cart journey | Complete: generated PostgreSQL, browser and regression gates passed 2026-10-22 |
| 6 | Offline payment simulator | Explicit simulation labels; failure/cancel/refund state tests | Complete for offline simulation: final PostgreSQL, browser, migration and regression gates passed 2026-10-22 |
| 7 | Razorpay test adapter | Official docs, signed notifications, reconciliation; real test-account evidence separately | Local implementation and checks passed 2026-10-23; phase remains open for real test-account evidence |
| 8 | Release verification | Independent functional/security/accessibility/performance reports, seeds, deployment/recovery instructions | Pending |

## Constraints and release policy

Use a modular monolith and reviewed reusable modules; keep model subtasks bounded.
Live payments remain disabled. No raw card data or credentials in generated test
workspaces. Tax/shipping/legal content must be explicit business configuration.
Never rewrite failing assertions silently. Version any justified test correction.
Keep existing workflows as regression fixtures. No phase is complete until its gate
passes. Offline simulation is not provider integration. No production-ready claim.

## Evidence and blockers

The latest fully completed phase is Phase 6 (offline payment simulation). Phase 7 local implementation and verification passed; actual provider evidence remains pending because the user has no test account yet. Phase 8 release verification remains pending.
Dated entries below retain earlier development evidence; the phase table is the current status.

### Phase 4 implementation and gate in progress — 2026-10-22

- Added typed identity configuration and reviewed IDENTITY generation with
  PostgreSQL migration 0002. Existing catalogue initial migration and sample
  applications are preserved. Configuration is validated again at runtime.
- Server sessions, scrypt passwords, login rotation, idle/absolute expiry,
  server-side logout, expiring single-use recovery and all-session revocation.
  Synchronizer CSRF and exact Origin apply to every write, including signup/login.
- Persistent account/IP/global rate limits, request-body bound, role checks,
  owned address operations and explicit administrator bootstrap. No default admin,
  public promotion endpoint or browser token storage. Local recovery outbox stays
  outside the served app; real SMTP delivery remains unverified.
- Transactional admin category/product/stock operations, product version conflicts,
  soft archiving/deactivated SKUs and bounded audit records. Responsive account and
  administration screens consume a shared versioned UI contract.
- Added mandatory platform-owned identity authority checks to every IDENTITY build.
  A negative permission result prevents VERIFIED independently of backend success.
  Model assertions remain unchanged; local compilation still uses four bounded
  sections with 2048-token limits. Mocked compiler verification is not a live LLM run.
- First generated PostgreSQL/browser gate passed. A later label improvement caused
  a TypeScript index-type error; the failure is retained at
  `docs/ecommerce-evidence/identity-typescript-failure.json`. Corrected the address
  key type and reran the build without changing the failing build criterion.
- Targeted unit tests passed and the preceding full suite passed 249 tests.
  Final expanded suite and final generated-app gate are running; do not treat this
  entry as phase completion. The final outcome will be recorded separately below.
- Operator guide/threat model/checklist: `docs/IDENTITY_GENERATOR.md`.
  Acceptance evidence: `docs/ecommerce-evidence/identity-verification.json`.

### 2026-10-19 foundation delivery

- `POST /api/projects/{id}/analyze?resume=true` explicitly reuses matching
  validated specialist checkpoints. Changed version/input/output recomputes the
  affected stage and later stages. No checkpoint means recomputation.
- `POST /api/projects/{id}/build?resume=true` explicitly reuses matching task
  output hashes and BuildSpec fingerprint. Invalidated dependencies cannot be
  reused after a second interruption. Generation checkpoints are atomically saved
  after each completed task; verification always reruns.
- New `UIContract` v1 supplies stable test IDs and live record identifiers.
  Opt-in declarative generation no longer infers controls from browser assertions.
  Old specs retain compatibility. No existing saved app was regenerated.
- Typed preparatory commerce contract covers relationships, ordered migrations,
  permissions, business rules, state transitions and test/simulator integration.
  Live mode and unknown configuration fields are rejected. **Schema support is
  not executable commerce support:** both compiler and CRUD generator block it.
- Backend regression command: `..\.venv\Scripts\python.exe -m pytest tests -q`
  from backend: **220 passed in 4.84s**. Includes legacy regression tests, recovery,
  dependency invalidation, corrupt checkpoint handling and contract validation.
  Windows tests require an unsandboxed local socket environment; the sandboxed
  attempt hung during asyncio setup and is not counted as passing evidence.
- `backend/verify_generator_foundation.py`: Docker-isolated TypeScript/Vite build
  and independent create/reload/edit/delete Playwright journey **passed**.
  Report: `docs/ecommerce-evidence/foundation-verification.json`.
  This verifies page reload, not database persistence across process restarts.
- Recovery behavior is exercised using deterministic test agents; this run did
  not perform a new six-agent live Nemotron integration run.
- Operator instructions: `docs/ECOMMERCE_RECOVERY.md`.

### Remaining work / next gate

Phases 2 and 3 have passed their acceptance gates. Phase 4 identity and permissions
This was the remaining-work note before Phase 4 resumed and is superseded by the
Phase 4 outcome below. Phase 5 is now active. Only real Razorpay provider evidence
requires external test credentials; no account is needed for Phase 5.

Reference material for later design review:
- PostgreSQL transaction isolation: https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL row locking: https://www.postgresql.org/docs/17/explicit-locking.html
- OWASP ASVS 5.0: https://github.com/OWASP/ASVS/tree/master/5.0
These references are not security verification results.

### 2026-10-21 resumed Phase 2

- Added a separate reviewed RELATIONAL_CRUD compiler and runtime for 2–12 entities,
  canonical CRUD routes, typed foreign keys, unique constraints and transactions.
  Existing single-entity compiler and saved applications are unchanged.
- Added checksum-checked initial migration 0001. Schema drift or existing
  unversioned application tables fail closed; automatic incremental/destructive
  schema changes are not supported.
- Added opt-in PostgreSQL development Compose configuration with a persistent
  volume and localhost-only port. Passwords must be supplied locally, never by
  model-generated source. Existing SQLite platform storage is unchanged.
- Added a separate PostgreSQL sandbox image using the existing restrictions:
  network disabled, unprivileged user, read-only root and resource limits.
  Its database is ephemeral and test-only; no live database secrets are passed.
- Local compiler chooses the relational strategy for multiple entities and keeps
  its bounded 2048-token sections. Test confirms the four-section path, original
  acceptance contract and reviewed runtime manifest. Live-model reliability has
  not been established by this mocked model test.
- Reviewed-runtime SQLite tests pass for related CRUD, uniqueness, foreign keys,
  required text, restart persistence, and migration checksum mismatch rejection.
- On resume the baseline passed: 223 tests. New compiler-path test also passed
  (7 local compiler tests). Full suite will be rerun after PostgreSQL verification.
- At resume Docker was stopped and the prior image download was incomplete.
  Docker was started and the trusted PostgreSQL image build resumed. Completion
  was withheld until the PostgreSQL constraints, process-restart, frontend-build
  and browser gates passed; see the outcome below.
- Scope limits: unauthenticated local development only; integer/text fields;
  frontend shows the first page; no commerce, ownership, payments or inventory
  reservation semantics are implied. Security/accessibility/performance remain
  unverified and are reported separately.
- Final regression run after compiler guards: **225 passed in 5.80s**. Includes
  generator implementation fingerprint invalidation and the bounded local-model
  multi-entity compiler path. One existing Starlette/httpx deprecation warning.
- SQLite isolated generated-app checks also passed: frontend build, backend
  schema test, and category/product relationship browser journey. Evidence:
  `docs/ecommerce-evidence/relational-sqlite-verification.json` and
  `docs/ecommerce-evidence/relational-sqlite-browser.json`. These results do not
  substitute for PostgreSQL evidence.
- PostgreSQL image setup now uses HTTPS, persistent apt download caches and
  bounded network timeouts/retries. This prevents an interrupted setup from losing
  all downloaded packages. Operator guide: `docs/RELATIONAL_GENERATOR.md`.

### Phase 2 acceptance outcome — 2026-10-21

- `backend/verify_relational_generator.py` **passed** with actual PostgreSQL 15
  and psycopg, not SQLite substitution. Generated 18 files in the separate
  `docs/ecommerce-evidence/relational-app` fixture.
- Build report: backend test, frontend TypeScript/Vite build, independent HTTP
  acceptance and browser journey all PASSED. Separate test terminated/restarted
  the backend process, checked persisted edits, rejected invalid foreign keys and
  duplicate values at both API and database levels, and exercised deletion order.
- Evidence: `docs/ecommerce-evidence/relational-verification.json`; source spec:
  `docs/ecommerce-evidence/relational-build-spec.json`. Original saved NoteKeeper
  and Task Manager applications were not regenerated.
- First PostgreSQL attempt failed because the sandbox initialized SQL-ASCII.
  Fixed initialization to UTF-8 and reran the same assertions successfully.
  Failure evidence retained in `postgresql-initial-encoding-failure.json`.
- The generator now refuses silent framework, styling, authentication or database
  provider substitution. Source recovery also fingerprints generator code.
- Completion is limited to initial versioned migrations and related CRUD, not
  incremental schema evolution or the full store. Generated development Compose
  configuration is provided; persistent-volume deployment is not yet release-
  verified. Live Nemotron end-to-end generation was not run in this gate.
- Security, accessibility, performance and provider integration remain unverified;
  no commerce readiness or production readiness is claimed.

### Phase 3 checkpoint — 2026-10-21, paused at user's request (historical)

- Implemented a reviewed, public read-only PostgreSQL catalogue module, typed seed
  contract, categories, variants/SKUs, integer minor-unit prices, local SVG images,
  search, same-variant price/stock filtering, sorting, pagination and product details.
- Added a responsive React/TypeScript storefront, CSS design tokens, shared UI
  selectors, loading/empty/error/retry states and native keyboard controls.
- Added catalogue strategy selection to the bounded local compiler and separate
  source-generation CLI. Legacy CRUD workflows remain covered by regression tests.
- Regression suite: **238 passed** before the latest scope/exporter guard edits.
  Catalogue unit cases: **13 passed**. Actual PostgreSQL acceptance, constraints
  and backend restart checks passed in the generated fixture.
- Browser failures were traced to the combined PostgreSQL/Vite/Chromium sandbox
  exhausting 128 processes/threads. Diagnostic logs show RuntimeError: can't start
  new thread and a PID range of 125–128. The reviewed PostgreSQL image now has a
  bounded 192-task allowance; memory, CPU, network and privilege limits remain.
- On the next run, rendered keyboard/layout/state checks passed. The verifier's
  final screenshot-count assertion failed because pytest prefixed the first PNG
  marker with a test label. The exporter was fixed and the image recovered. The
  complete verifier has NOT yet been rerun after this fix; Phase 3 is not complete.
- Evidence lives in `docs/ecommerce-evidence/catalogue-verification.json`, the
  diagnostic JSON files, and `catalogue-desktop-catalogue.png`,
  `catalogue-mobile-catalogue.png`, `catalogue-mobile-detail.png`.
- Initial visual inspection found a persistent visible skip-link overlay in
  screenshots and hero lettering clipped by the rounded illustration boundary.
  Review and fix those before the final rendered acceptance run. Preserve keyboard
  skip-link behavior; do not remove accessibility checks to hide the issue.

Resume with: finish visual corrections, add a mocked catalogue compiler-path
regression, rerun the final backend suite and `backend/verify_catalogue_generator.py`,
inspect fresh desktop/mobile screenshots and record final evidence. Accounts,
administration, carts, checkout and payments remain future phases. No assertion
was weakened to pass the checks. No new live Nemotron generation run was performed.

### Phase 3 acceptance outcome — 2026-10-22

- Resumed on user instruction and completed the public catalogue phase.
- Fixed keyboard skip-link styling without removing the link or its focus checks.
  It is visually clipped while unfocused and fully visible for keyboard focus.
  The hero caption now fits within its rounded illustration at desktop/mobile sizes.
- Added the deterministic bounded local-compiler catalogue regression: four model
  sections, 2048-token output limits, reviewed strategy/manifest selection and
  unchanged supplied API/browser assertions. This does not claim a live-model run.
- The final backend regression suite passed: **239 tests in 8.43s**, with one
  existing Starlette/httpx deprecation warning.
- `backend/verify_catalogue_generator.py` completed successfully against the final
  generated source: **27 files**, backend test PASSED, TypeScript/Vite frontend
  build PASSED, independent API acceptance PASSED, browser journey PASSED.
- Separate actual PostgreSQL constraints/restart check PASSED. Separate rendered
  browser check PASSED at 1440, 1024, 390 and 320 pixel widths. It exercises keyboard
  skip/variant controls, search/filter/sort/pagination, loading while a real request
  is held, empty/error/retry behavior, image failure fallback and malformed links.
- The malformed-link assertion caught Vite rejecting invalid URI escapes before
  React ran. Added a dev/preview request guard and retained the assertion. The build
  then caught a middleware type-declaration issue; its structural request type was
  corrected and the TypeScript build rerun successfully. Failure evidence retained
  in `catalogue-malformed-path-failure.json` and `catalogue-vite-type-failure.json`.
- Inspected fresh desktop catalogue, mobile catalogue and mobile detail PNGs.
  No persistent skip overlay, clipped hero caption, overlapping product labels or
  horizontal page overflow was observed. Keyboard/layout checks are targeted,
  not a comprehensive accessibility certification. Details and screenshot hashes:
  `docs/ecommerce-evidence/catalogue-visual-review.md` and `catalogue-verification.json`.
- Final generated-source digest:
  `7fc23b7d1b4ff3a6cafdaa70dc4398a56549f29cacefd5f215f5259e68d87f37`.
- Operator instructions: `docs/CATALOGUE_GENERATOR.md`. Generated example source:
  `docs/ecommerce-evidence/catalogue-app`. Existing saved NoteKeeper/Task Manager
  application directories were not regenerated.
- Remaining boundaries: public read-only catalogue, reviewed local SVG assets,
  immutable initial migration and sample seed content. No customer accounts,
  admin mutations, cart, checkout, inventory reservations or payments are claimed.
  Security and performance remain UNVERIFIED; provider integration is NOT_IMPLEMENTED.
  Full e-commerce generation and production readiness are not claimed.

### Phase 5 acceptance outcome — 2026-10-22

- Added the reviewed `ORDERS` compiler/runtime: account-owned carts, server pricing
  from integer minor-unit prices, versioned quotes, explicit tax/shipping/discount
  rules, owned-address validation, order-item/address/policy snapshots, per-user
  idempotency keys, temporary inventory reservations, cancellation and expiry.
  Checkout and stock administration share a transaction advisory lock in PostgreSQL.
- Added checksum-checked migration 0003 for `carts`, `cart_items`, `orders` and
  `order_items`; existing 0001/0002 migration history is required. The generator
  composes exactly 40 unique files, at the existing compiler's 40-file bound.
- Added platform-owned order-integrity and order-browser gates to every ORDERS
  build. They are independent of model-written tests. A failed order or rendered
  order journey prevents VERIFIED status. The UI exposes unpaid status clearly;
  it does not imply payment or fulfillment.
- Generated build `ORDERS-DEMO` in `docs/ecommerce-evidence/orders-app` passed:
  backend test, TypeScript/Vite build, frozen catalogue acceptance, catalogue
  browser journey, identity authority gate, four PostgreSQL order-integrity tests,
  and the rendered account/cart/checkout/cancellation/admin-denial journey. All
  seven verification checks are PASSED; build status is VERIFIED. The four order
  integrity tests confirmed the real PostgreSQL dialect and all three migrations,
  server-authoritative totals, immutable snapshots, idempotency, cancellation and
  expiry release-once behavior, ownership, stale quote rejection, a simultaneous
  last-unit checkout (one success, one conflict), and data persistence through two
  backend process restarts.
- `backend/verify_orders_generator.py` rerun completed successfully after two test
  corrections. The first new gate had incorrectly expected a price change to make
  inventory unavailable; live behavior correctly rejected the stale quote while
  keeping the available product purchasable. The assertion was changed to check
  stale quote rejection and that the out-of-stock SKU was not added. Initial browser
  evidence captured a loading state; the journey now waits for loaded order history
  before taking its mobile screenshot. No product assertion was weakened.
- Desktop cart and 390px mobile order history screenshots were inspected. Both
  include the loaded page, show no clipped cart/checkout controls or horizontal
  overflow. This is targeted responsive/browser evidence, not an accessibility
  certification. Screenshot hashes and the build report are in
  `docs/ecommerce-evidence/orders-verification.json`; operator instructions are in
  `docs/ORDERS_GENERATOR.md`.
- Full backend regression suite: **263 passed in 107.02s**, with one existing
  Starlette/httpx deprecation warning. Existing NoteKeeper and Task Manager saved
  applications were not regenerated.
- Generated source digest:
  `2f2e352564649d5db78b1b35174d219ea3ce4d0132ec417252ff2fa517b0850e`.
- Remaining limits: this phase creates unpaid orders only. Payment simulation,
  provider integration, refunds and fulfillment remain disabled and are not
  verified. Performance/load testing, full OWASP ASVS conformance, independent
  penetration testing, deployment hardening and live email delivery remain
  unverified. The global Postgres advisory lock favors safety for a small store and
  will constrain write throughput. Do not claim production readiness.
- Next phase: Phase 6, the explicitly labelled offline payment simulator, with
  separate pending/success/failure/cancel state tests. It must never count as
  provider integration evidence.


### Phase 4 acceptance outcome — 2026-10-22

- Phase 4 completed for reviewed customer identity, owned addresses and authorized
  catalogue administration. Independent gates passed against final generated
  source: **36 files**, backend tests, TypeScript/Vite build, API acceptance,
  catalogue browser journey and mandatory identity authority checks.
- Final full backend regression run: **251 passed in 95.17s**, one existing
  Starlette/httpx deprecation warning. A final recovery fingerprint refinement
  includes copied spec validators/UI manifests; its five focused tests also passed.
- Separate real PostgreSQL security/restart check PASSED (8.71s). Separate browser
  account/admin/layout check PASSED (19.16s), including real product creation and
  archiving, address editing/deletion, keyboard login and customer admin denial.
- Inspected all four final PNGs. No clipping/label overlap or horizontal overflow
  was observed. Evidence and image hashes: identity-verification.json,
  identity-regression-results.json and identity-visual-review.md under
  docs/ecommerce-evidence. Earlier TypeScript failure evidence is retained.
- Password recovery expiry/reuse/revocation, current-password change, idle and
  absolute expiry, HTTPS cookie flags, rate-limit persistence, input redaction,
  server-only local recovery outbox and failed-authority gating have targeted tests.
  The local compiler path has bounded mocked-model evidence, not a live Nemotron run.
- Final generated-source digest:
  `ada8766f61b75e51e30cbc0a7d929944b7196feea434d1c9fc1ed8e0081ba014`.
- Operator setup and threat model/applicable ASVS checklist:
  docs/IDENTITY_GENERATOR.md. Source: docs/ecommerce-evidence/identity-app.
  Existing NoteKeeper and Task Manager saved source directories were not regenerated.
- Remaining limits: no real SMTP delivery evidence, full ASVS conformance,
  independent penetration test, dependency/secret scan, load test or production
  deployment verification. Admin pagination beyond the 200-record bound, MFA,
  email verification and category concurrency versioning remain improvements.
- Next is Phase 5: server-authoritative carts, order-item price snapshots,
  idempotent order creation, inventory reservations and concurrent overselling
  checks. Payment simulation/provider adapters remain Phases 6/7; live payments
  remain disabled. No production-ready claim is made.

### Phase 6 work in progress — 2026-10-22

- Added typed offline-only simulation contract and reviewed PAYMENT_SIMULATOR composition.
- Added transactional PostgreSQL migration 0004, pending/success/failure/cancellation,
  server amount/currency checks, event idempotency, owner/CSRF/admin checks, full refunds
  and explicit simulation UI. No external payment provider or credentials are involved.
- Initial generated 44-file build passed all nine mandatory checks. Added phase-5
  migration-preservation gate also passed; focused regressions: 32 passed.
- Final pass adds persistent simulation action rate limits and reruns the complete suite
  and generated-app gate. Completion withheld until final evidence is recorded.
- A pytest parameter named request was rejected during collection; renamed description.
  No application assertion was changed. Earlier screenshot review found no clipping.

### Phase 6 acceptance outcome — 2026-10-22

- Completed reviewed PAYMENT_SIMULATOR generation with an explicit offline-only
  typed contract, PostgreSQL migration 0004, session/CSRF/ownership enforcement,
  rate-limited simulation actions and persistent event idempotency/audit records.
- Pending simulations can succeed, fail or cancel. Late/contradictory outcomes
  fail; failure/cancellation/expiry release stock once. Success consumes the
  reservation and cannot be cancelled through the unpaid-order endpoint.
- Only administrators can create full simulated refunds. Pending/failed/successful
  refund states persist; failed refunds can be retried, and success restores stock
  exactly once. This stock policy assumes fulfillment remains disabled.
- Generated 44-file fixture: docs/ecommerce-evidence/payments-app. The final build
  passed all NINE mandatory checks: backend tests, frontend build, frozen requirement
  acceptance, catalogue browser journey, identity authority, order integrity,
  order browser journey, payment simulation API and payment simulation browser.
- The 10 PostgreSQL simulation cases passed, covering amount/currency tampering,
  duplicate/conflicting/late outcomes, CSRF and owner/admin checks, release-once
  behavior, refund retry, concurrent opposing outcomes, two process restarts,
  persistent rate limits and an actual 0003-to-0004 migration preserving an order.
  Old phase-5 code rejects the upgraded schema rather than interpreting it wrongly.
- The rendered journey passed account/address/cart/checkout, simulation success
  and failure, persisted reload, customer admin denial, and admin failed-refund
  retry followed by a successful refund. Inspected final desktop/mobile screenshots;
  simulation labels are explicit, controls readable, no horizontal overflow observed.
- Full backend regression suite: 275 passed in 115.54 seconds; one existing
  Starlette/httpx deprecation warning. Final compiler/documentation refinements:
  21 focused tests passed. Initial pytest collection failed because request was a
  reserved parameter name; renamed it without changing an assertion.
- Order gate compatibility extension v2: ORDERS still requires exactly migrations
  0001–0003 and payment_status=not_implemented. PAYMENT_SIMULATOR requires exactly
  0001–0004 and payment_status=not_started before any attempt. This documents the
  new module contract; prior order invariants and assertions remain mandatory.
- Reviewed simulator manifest permits at most 48 unique paths (44 generated),
  while older strategies retain the 40-file bound. Local compiler sections remain
  at 2048 tokens. No larger model context/hardware requirement was introduced.
- Evidence: docs/ecommerce-evidence/payments-verification.json and
  payments-regression-tests.log. Guide: docs/PAYMENT_SIMULATOR.md. Source digest:
  `a1990d74252e10f08a99534ee4ca3992d0888ccbd14cdece81779d6dd5db1dfb`.
- Existing NoteKeeper, Task Manager, catalogue, identity and order sample source
  folders were not regenerated or migrated. Only disposable verification databases
  were upgraded; development data migration requires the documented setup.
- Limits: this is a prepared-spec generator fixture, not a fresh six-agent live
  Nemotron end-to-end run. No bank/provider requests, real charges, raw cards,
  partial refunds, fulfillment or provider reconciliation exist. Provider evidence
  remains NOT_IMPLEMENTED, performance/load UNVERIFIED, and security/accessibility
  evidence is targeted only. Do not claim production readiness.
- Next: Phase 7, a separate Razorpay TEST adapter with signature checks, webhook
  ordering/deduplication, reconciliation and authorized refunds. Actual provider
  verification requires test-account credentials; live payments remain disabled.

### Phase 7 local delivery — 2026-10-23

- Added separate RAZORPAY_TEST generation and typed non-secret contract. The reviewed
  46-file PostgreSQL fixture is docs/ecommerce-evidence/razorpay-app. Its checksummed
  0004_razorpay_test migration branches from phase-5 ORDERS, not simulator 0004.
  Earlier source samples and user databases were not modified or migrated.
- Provider client uses fixed HTTPS API, bounded requests/responses, no redirects,
  server-only secrets and an explicit rzp_test_ key guard. Live keys fail closed.
  Official Checkout is loaded on request. No application card form or stored raw
  card/webhook payload. Documented references: docs/RAZORPAY_TEST_GENERATOR.md.
- Durable order intents, receipt lookup after lost responses, server price/currency
  matching, callback HMAC plus fetched capture evidence, raw-body webhook HMAC,
  account binding, persisted event deduplication and explicit reconciliation.
- Authorized/failed/delayed events cannot assert capture or regress paid state.
  Late captures after reservation release require admin review/refund and never
  reclaim stock. Dashboard-issued refunds are flagged for review, not auto-restocked.
- Administrator-only full test refunds use saved X-Refund-Idempotency keys and the
  same payload. Pending/failed/processed states persist; processed refunds restore
  stock once. A separate authorized retry endpoint recovers uncertain requests
  using the server's original key even if browser storage was lost.
- Bounded compiler retains four 2048-token sections, shared payment UI selectors
  and unchanged acceptance assertions. Simulator and provider contracts are mutually
  exclusive. Existing order checks now explicitly recognize provider migration
  0004_razorpay_test and initial not_started status; legacy expectations remain intact.
- Full backend regression suite: **292 passed in 178.25 seconds**, one existing
  Starlette/httpx deprecation warning. Focused compiler/client tests: 17 passed.
- Final generated fixture: all NINE local gates PASSED (backend, frontend build,
  acceptance, catalogue browser, identity authority, order integrity, order browser,
  synthetic Razorpay contract, Razorpay browser). Provider contract gate: **14 passed**,
  including invalid signatures, amount/currency/ID/capture checks, ownership/CSRF,
  missing credentials/live guard, lost create/refund responses, replay/out-of-order
  webhooks, expiry/cancel late capture, failed-refund retry, cross-session recovery,
  concurrent callback/webhook, persistent rate limits, a fresh server process, and
  an actual phase-5 database upgrade preserving order data and rejecting downgrade.
- Browser checked real account/cart/order flow, unavailable-provider state, mocked
  official Checkout script, server-verified synthetic capture, reload, keyboard
  reconciliation and customer denial of admin orders. Inspected desktop 1440px and
  mobile 390px screenshots: readable labels, no clipping or horizontal overflow.
  Provider-hosted UI and administrator refund UI were not inspected against a real
  provider; refund API behavior has local contract evidence.
- Evidence: docs/ecommerce-evidence/razorpay-verification.json,
  razorpay-regression-tests.log, razorpay-local-run.log and razorpay-{desktop,mobile}.png.
  The generated .projectforge directory retains individual gate results.
- Test infrastructure corrections: the browser test initially tried writing its
  synthetic helper to the read-only source mount; moved only that helper to /tmp.
  A huge pytest parameter label exceeded Windows environment limits; gave it a short
  ID without changing the oversized-response assertion. A browser retry accidentally
  selected the base image; corrected to the PostgreSQL image. Docker was stopped on
  resume and was started before final verification. No failing assertion was weakened.
- The earlier usage-limit interruption prevented approval review of a test rerun;
  testing resumed successfully after the user returned on 2026-10-23.
- **Phase 7 is not fully complete:** user requested local work first and has no
  Razorpay test account. Real Checkout, signed provider webhook delivery and provider
  refund round trips remain UNVERIFIED. Local mocks are never counted as provider
  integration. Every RAZORPAY_TEST build intentionally remains REQUIRES_HUMAN with
  razorpay_provider_integration=UNVERIFIED even when local checks pass.
- Remaining: real test-account evidence and an approved staging webhook endpoint;
  a reviewed external-evidence promotion workflow; then Phase 8 release checks.
  No live payments, fulfillment, partial refunds, scheduled reconciliation, automatic
  webhook-secret rotation, retention cleanup, full security/accessibility audit,
  load testing or production-readiness claim. This is prepared-spec generation,
  not a new live six-agent Nemotron run. Secrets were not requested or configured.

### Narrow delivery status increment — 27 October 2026

- User authorized only administrator marking of packed, shipped and delivered,
  then stopping. Implemented for the current payments-app and razorpay-app demos
  and their reusable generation modules. Unpaid ORDERS generation remains bounded
  to its previous scope; no NoteKeeper or Task Manager files were changed.
- Separate additive 0005_delivery migration stores order_fulfillment; prior
  migration definitions/checksums remain unchanged. No user database was accessed
  by the tests. Updated application startup/migrate.py applies the new table.
- Admin session + CSRF required. Ordered, stale-safe transitions; repeated steps
  are no-ops. Paid demo orders only, with active-refund exclusion. Customer order
  history exposes the saved status through existing ownership-filtered routes.
- Delivery does not change stock or financial state. Refund initiation is blocked
  after packing because returns are outside this increment. Existing provider
  refund processing does not restore dispatched/packed goods automatically.
- Acceptance evidence: 13 simulator/API checks, 15 synthetic provider checks,
  one real browser journey through all three buttons, and 29 generator checks
  passed. Both demo frontend builds passed. Inspected desktop/mobile screenshots.
- Evidence and activation steps: docs/delivery-evidence/DELIVERY_STATUS.md.
  Test contract v2 adds the exact new migration revision and two generated source
  assets; old financial/security assertions remain. Initial failed runs retained.
- Stopped at this requested boundary: no courier, tracking number, notification,
  returns, real dispatch or live-payment work. Real provider verification and the
  broader release/security phase remain incomplete.
