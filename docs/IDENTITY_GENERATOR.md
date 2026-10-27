# Phase 4: accounts and authorized catalogue administration

This is a reviewed source-generation module, not arbitrary model-written security
code. React/TypeScript and FastAPI remain unchanged. Generated applications use
PostgreSQL and immutable migrations 0001 (catalogue) and 0002 (identity). Existing
SQLite NoteKeeper and Task Manager projects are not rewritten.

## Generation and execution

Use `catalogue_contract` plus `identity_contract` version 1, PostgreSQL, plain CSS
and `auth_provider: session`. The bounded local compiler selects `IDENTITY`, keeps
four sections with 2048 output tokens each, and installs the reviewed manifest.
It preserves supplied acceptance assertions. This compiler route has a mocked
regression; no new live Nemotron run is claimed by the deterministic fixture.
Cart, checkout, orders, payments, uploads and marketplace requests still fail scope
validation rather than receiving an incomplete CRUD substitute.

The generated example is `docs/ecommerce-evidence/identity-app`. To regenerate
and verify it from the repository backend directory:

```powershell
..\.venv\Scripts\python.exe verify_identity_generator.py
```

Requires the existing `projectforge-relational-runtime:local` Docker image.
It runs without external networking and uses synthetic test-only credentials.
The separate independent PostgreSQL/browser tests live outside generated source
under `.projectforge`. Generation checkpoints are reused only explicitly with
`generate_identity.py --spec SPEC.json --output DIRECTORY --resume`; source/spec
fingerprint changes invalidate reuse. Verification always reruns.

To run a generated app manually, follow its README. Start the generated PostgreSQL
service using `backend/compose.yaml` with a locally chosen POSTGRES_PASSWORD,
set DATABASE_URL to that service, run `python migrate.py`, then create an admin
with `python manage.py create-admin --email you@example.com`. The command prompts
for a passphrase; no default password or public promotion endpoint exists.
The optional `--password-env` flag is for synthetic automation only. Do not pass
a real password on the command line or include it in agent contexts.

For local demonstration, set public_origin to `http://127.0.0.1:3001` and
allow_local_http=true in `backend/app/identity.json`. Bind the backend to loopback
port 8001 with `--no-proxy-headers`; Vite serves port 3001 and proxies API requests.
HTTP development rejects non-loopback clients. HTTPS is the default configuration
and uses a Secure `__Host-` session cookie. Configure a trusted TLS termination
proxy and exact public origin before deployment; arbitrary forwarded client IP
headers must not be trusted for rate limits.

## Data and authority

| Table/addition | Purpose and ownership |
|---|---|
| users | Unique normalized email, display name, scrypt hash, customer/admin role, active flag and credential epoch |
| sessions | SHA-256 hash of random cookie, user FK, synchronizer CSRF token, timestamps and credential epoch |
| password_resets | SHA-256 hash of random token, user FK, expiry and used flag |
| addresses | User FK and address fields; all reads/writes constrain the authenticated owner |
| rate_limits | Hashed account/IP/global bucket keys and atomic persistent counters |
| audit_records | Actor FK, operation, resource ID and time; no password, token, request body or full address |
| products.version | Optimistic concurrency check shared by product and stock writes |

Anonymous pre-authentication sessions expire after 15 minutes. Customer/admin
sessions expire after 30 minutes idle and 8 hours absolute by default; configurable
bounds are in IdentityContract. At most five authenticated sessions per account
are retained; a new login removes the oldest session when necessary. Successful
login rotates the pre-auth session. Logout revokes it server-side. Password change
and recovery revoke all sessions and all outstanding recovery links. User-row
locks serialize credential changes and concurrent session creation.

Passwords use salted scrypt N=131072, r=8, p=1, with a one-at-a-time hash semaphore
to bound memory use on student hardware. Passphrases are 15–128 characters; a small
common-password denylist is not a comprehensive breached-password check. See the
[OWASP storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Do not describe this implementation as meeting every authentication standard.

Every write requires exact Origin plus a synchronizer CSRF token tied to the
current session, including login and signup; cross-site Fetch Metadata is rejected.
SameSite=Lax is supplementary. Credentials stay in HttpOnly cookies and component
memory, never localStorage. See [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

Recovery uses 256-bit random, hashed, single-use tokens expiring in 15 minutes.
Responses conceal account existence; the URL token is placed in a fragment and
cleared by the UI. Local delivery is a server-only temporary JSON outbox outside
the served app. Operators must protect it with OS permissions (POSIX modes alone
are not a Windows ACL policy). HTTPS SMTP STARTTLS delivery is an optional server
adapter; credentials and real email delivery are external and unverified. There is
no public token-reader endpoint. See [OWASP recovery guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

Admin operations check the database-backed role. Product edits and stock changes
require the current product version; stale requests return 409. Database uniqueness
and FK failures roll back the whole transaction. Archiving is soft deletion;
omitted SKUs are deactivated to preserve identifiers. Local image assets are
allowlisted and no upload or remote image-fetch endpoint is available. Admin list
and audit responses are bounded to 200 records; catalogue-scale admin pagination
is a future improvement. Category toggles are transactional but do not yet have
optimistic version checks. Stock here is catalogue stock, not inventory reservations.

## Threat model and applicable security checklist

Assets: customer PII, credential hashes, sessions, recovery tokens, catalogue prices
and stock, admin authority and audit integrity. Threat actors: anonymous attacker,
malicious customer, CSRF origin, stolen token holder and compromised dependency.
Trust boundaries: browser/server, server/PostgreSQL, server/mail and generated-code
sandbox/host. TLS, database administration, mailbox security and host operator
permissions are deployment responsibilities. A compromised admin can change
catalogue data; an audit record does not prevent that abuse.

This is a scoped checklist against [ASVS 5.0](https://owasp.org/projects/asvs),
not a claim of ASVS certification or full Level 1/2 conformance. The session item
numbers below follow the [official V7 chapter](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md).

| Control / threat | Implementation | Evidence / release boundary |
|---|---|---|
| ASVS 7.2.1–7.2.4: server validation, unpredictable tokens, rotation | Server sessions, random 256-bit tokens, cookie hashing, login rotation | Targeted runtime tests; no formal entropy certification |
| ASVS 7.3.1–7.3.2: idle/absolute expiry | Independent timestamps and validated bounds | Clock-driven expiry tests |
| ASVS 7.4.1: termination | Logout and credential epoch/session deletion | Revocation/recovery/restart tests |
| ASVS 7.1.1–7.1.2: documented lifetime/concurrency | 30-minute idle, 8-hour absolute, maximum five sessions | Above policy; deployment risk review still required |
| CSRF and session fixation | Exact Origin, CSRF token, Lax/HttpOnly/Secure flags | Negative requests and HTTPS cookie tests |
| Credential stuffing / resource exhaustion | Persistent account/IP/global counters; body bound and hash semaphore | Rate-limit restart and oversized body tests; load testing UNVERIFIED |
| IDOR / privilege escalation | Owner-scoped address operations, server-only roles, forbidden input extras | Cross-owner/role negative tests, PostgreSQL constraints |
| Password recovery abuse | Generic response, expiring hashed token, single use, session revocation | Targeted tests; real SMTP delivery UNVERIFIED |
| Injection/XSS | Parameterized SQL, Pydantic allowlists, React text rendering, local image whitelist | Targeted validation tests; independent penetration test UNVERIFIED |
| Lost stock edits | Product version check and database transactions | Stale update and conflicting-SKU rollback tests |
| Secret exposure | No default credentials; redacted validation; bounded audit data | Synthetic fixture checks; complete repository secret scan UNVERIFIED |
| Generated-code escape | Offline network, unprivileged user, read-only root, resource limits | Existing executor regression; formal isolation audit UNVERIFIED |
| Supply chain | Prebuilt reviewed runtime with bounded dependencies | Dedicated dependency vulnerability scan UNVERIFIED |
| Sensitive operation reauthentication / MFA | Current password required for password change | Admin step-up/MFA, email verification and breached-password service NOT_IMPLEMENTED |
| Transport, CSP, backups and monitoring | Deployment configuration required | TLS termination, browser CSP, backup/restore and alerting UNVERIFIED |

Functional, targeted security, accessibility, performance and provider results are
separate in `identity-verification.json`. Passing these tests does not establish
production readiness. Phase 5 must add server-authoritative carts, orders, snapshots,
inventory reservations, idempotency and concurrent overselling tests before checkout.
