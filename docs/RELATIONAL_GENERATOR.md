# Related-data generator: Phase 2

This module generates a local, unauthenticated React/TypeScript + FastAPI CRUD
application with 2–12 related entities. It is the data foundation for the planned
store generator, not an e-commerce application or a production deployment.

## Supported contract

Use `source_generation_strategy: RELATIONAL_CRUD`, a `relational_contract` with
version 1, and SQLite or PostgreSQL in `tech_stack.primary_database`. Every entity
has one integer primary key, integer/string/text fields, and explicit uniqueness
and nullability. Relationships name both tables and columns and one of RESTRICT,
CASCADE or SET NULL. Invalid references and incompatible types are rejected.

Routes are GET/POST `/api/TABLE` and PUT/DELETE `/api/TABLE/{record_id}`. PUT
requires all non-primary fields. Unknown fields, supplied primary keys, blank
text and invalid types are rejected. Duplicate/foreign-key failures return 409;
missing update/delete targets return 404. Every mutation runs in a transaction.

Initial migration 0001 is stored with the generated source. Startup verifies its
manifest against the schema and its checksum against the database. Repeated
startup is idempotent; modified or unversioned databases require a reviewed
migration rather than being erased or silently adopted. Incremental schema
migrations are a later extension, not implemented by this initial migration.

## Trusted test runtime setup

Keep Docker Desktop running. From the project root:

```powershell
docker build -t projectforge-relational-runtime:local -f backend/sandbox/Dockerfile.relational backend/sandbox
cd backend
..\.venv\Scripts\python.exe verify_relational_generator.py
```

Building the trusted image requires internet initially. Tests then run with
network disabled in an unprivileged, read-only, resource-limited container.
PostgreSQL is temporary inside that container and accepts only its local Unix
socket. The test authentication configuration must never be used for deployment.

The verifier creates a separate example under
`docs/ecommerce-evidence/relational-app`, preserving existing user projects. It
saves the explicit example specification and structured verification results next
to that folder. It tests the generated browser journey and PostgreSQL behavior,
including terminating and restarting the backend process against the same data.

## Generate from a reviewed specification

```powershell
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe generate_relational.py --spec ..\docs\ecommerce-evidence\relational-build-spec.json --output ..\docs\ecommerce-evidence\my-related-app
```

Use `--resume` to reuse matching source checkpoints while rerunning verification.
The compiler supplies the reviewed source manifest; it does not replace failing
acceptance assertions. The ordinary local-model section compiler can also choose
this strategy for related entities. Its deterministic mocked test is not proof
that every local-model prompt will succeed.

## Run a generated PostgreSQL application

Install the generated backend requirements in a virtual environment. From its
backend directory, set `POSTGRES_PASSWORD` to a password chosen locally and run
`docker compose up -d --wait`. Configure the server-only `DATABASE_URL` using
`postgresql+psycopg://projectforge:PASSWORD@127.0.0.1:5432/generated_app`, with the
password URL-encoded. Keep credentials out of version control and frontend code.

Run `python migrate.py`, then `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
In a separate terminal from generated frontend run `npm install --ignore-scripts`
and `npm run dev`, then open http://127.0.0.1:3001. The development Compose database
uses a persistent named volume. Do not use `docker compose down -v` unless you
intend to delete its data. This Compose setup is separate from the ephemeral test
database and has not been described as production hosting.

## Remaining limits

- No authentication, permissions, checkout, money calculations or reservations.
- The initial UI exposes a form per entity; foreign keys use numeric inputs.
- API supports limit/offset; the initial UI displays the first page only.
- No incremental migration generation, uploads or custom business endpoints.
- Security, accessibility, performance and payment integration remain separate,
  unverified release gates. Functional verification does not certify a store.
