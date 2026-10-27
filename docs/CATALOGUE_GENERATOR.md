# Phase 3: public catalogue generator

ProjectForge can generate a read-only catalogue with categories, products,
variants/SKUs, local product illustrations, price and stock filters, search,
sorting, pagination and product-detail galleries. Its React/TypeScript frontend
uses reusable CSS tokens and a shared selector contract. The application backend
uses FastAPI and PostgreSQL; ProjectForge's own persistence remains SQLite.

## Files to inspect

- Example source: `docs/ecommerce-evidence/catalogue-app`.
- Reviewed example specification: `docs/ecommerce-evidence/catalogue-build-spec.json`.
- Verification report: `docs/ecommerce-evidence/catalogue-verification.json`.
- Screenshots: `catalogue-desktop-catalogue.png`, `catalogue-mobile-catalogue.png`
  and `catalogue-mobile-detail.png` in that evidence directory.
- Runtime/compiler: `backend/app/execution/agent/catalogue.py`,
  `catalogue_runtime.py`, and `catalogue_templates`.
- Data/UI contracts: `backend/app/execution/spec/catalogue_contract.py` and
  `catalogue_ui.py`.

The example is a separate generated application. Existing NoteKeeper and Task
Manager source directories are preserved.

## Reproduce the isolated verification

Start Docker Desktop. The trusted PostgreSQL runtime image must already exist;
its initial build needs internet. From a PowerShell terminal:

```powershell
cd D:\capstone_project\backend
$env:Path += ';C:\Users\HET\AppData\Local\Programs\DockerDesktop\resources\bin'
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe verify_catalogue_generator.py
```

The verifier generates the example and runs PostgreSQL, TypeScript/Vite, API,
browser, keyboard and layout checks inside the restricted container. Its database
is temporary and receives no live credentials. It captures actual PNG renders
and records their hashes. It does not call LM Studio or a hosted model.

To generate a separate copy from a reviewed specification:

```powershell
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe generate_catalogue.py --spec ..\docs\ecommerce-evidence\catalogue-build-spec.json --output ..\docs\ecommerce-evidence\my-catalogue
```

Add `--resume` to reuse matching source checkpoints while rerunning verification.
Acceptance cases remain frozen; editing seed content may require a new, reviewed
acceptance contract. Do not change assertions simply to obtain passing results.

## Run the generated example for a demonstration

Open `D:\capstone_project\docs\ecommerce-evidence\catalogue-app` in VS Code.
Follow that application's README. It supplies a PostgreSQL Compose service with
a persistent named volume. Choose a local development database password and set
`POSTGRES_PASSWORD` in the terminal; no password is supplied or stored by agents.

From the generated `backend` folder:

```powershell
docker compose up -d --wait
```

Install the generated backend requirements in a virtual environment. Configure
the server-only `DATABASE_URL` with
`postgresql+psycopg://projectforge:URL_ENCODED_PASSWORD@127.0.0.1:5432/catalogue`.
Then run:

```powershell
python migrate.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

In a second terminal, from the generated `frontend` folder:

```powershell
npm install --ignore-scripts
npm run dev -- --host 127.0.0.1 --port 3001 --strictPort
```

Open http://127.0.0.1:3001. ProjectForge itself uses ports 8000 and 3000; the
generated example uses 8001 and 3001. Initial installation/image pulls need
internet. The generated catalogue itself uses local data and local SVG assets.

## Data and scope

The `CATALOGUE` strategy accepts a validated `catalogue_contract` and the four
public GET endpoints. It does not silently substitute for a full commerce request.
The local model compiler retains bounded sections; a deterministic regression
test proves strategy selection and preservation of acceptance cases. A new live
Nemotron generation run is separate from that test and is not implied.

The example data is explicitly seed/sample content. Prices use integer minor
units and a declared INR/USD/EUR/GBP currency. Filters for price and stock match
the same active SKU. Inactive products, categories and variants are hidden.
Images come from reviewed local SVG assets; remote fetching and uploads are not
implemented. Seed data is applied once and never overwrites edits on restart.
The current immutable initial migration rejects drift; incremental schema
migrations remain a later extension.

The current storefront is a catalogue preview. Accounts and authorized admin
editing are Phase 4. Cart/order/inventory reservations are Phase 5. Simulation
and provider payment integration are later gates. Stock shown here is a snapshot,
not a reservation or overselling guarantee. Functional and targeted accessibility
checks do not constitute a full security, accessibility, performance or production
readiness assessment. No 60-FPS, load, or provider-integration claim is made.
