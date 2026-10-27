# Explicit recovery and verification

The existing default endpoints still start fresh work. Opt in to recovery with
`?resume=true`. Replace `PROJECT_ID` with the existing project ID. Keep the
FastAPI backend and local model running. Do not send multiple concurrent builds.

```powershell
# Resume validated specialist stages after interruption:
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/projects/PROJECT_ID/analyze?resume=true"

# Resume completed source tasks, then rerun all verification:
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/projects/PROJECT_ID/build?resume=true" -TimeoutSec 900
```

Analysis recovery requires a matching requirement version and input fingerprint,
and exactly matching saved specialist output. Recomputed stages invalidate later
reuse. Old projects without checkpoints safely recompute. Conflicts and build-spec
compilation run again. Recovery does not grant guided-build approval.

Build recovery checks the full BuildSpec and hashes of all task-owned outputs.
Missing/changed outputs cause regeneration of that task and its dependants. Each
completed task is saved atomically. If verification failed, intact source may be
reused but verification always reruns. Source-task reuse is not test success.
Generator source changes automatically invalidate source reuse through an
implementation fingerprint. A corrupted checkpoint grants no reuse.

`TASK_RECOVERED` and `AGENT_RECOVERED` events identify reused work. The existing
`tasks_executed` report counts tasks executed on this attempt, not reused tasks.

## Shared UI contract

New specs can opt into `ui_contract: {"version": 1, "namespace": "tasks"}`.
The declarative frontend exposes `data-testid="tasks-create"`, `tasks-save`,
`tasks-list`, `tasks-row`, `tasks-edit`, `tasks-delete`, `tasks-error`,
`tasks-loading`, and `tasks-field-FIELDNAME`. Row controls carry the actual
`data-record-id`. `UIContract.selector()` generates selectors for independent
tests. Test values are not used to construct controls. Old specs retain their
legacy selectors. This contract currently covers CRUD, not a storefront.

## Reproduce isolated foundation checks

With Docker Desktop running and `projectforge-runtime:local` available:

```powershell
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe verify_generator_foundation.py
```

The smoke test writes a separate application under
`docs/ecommerce-evidence/foundation-app` and a machine-readable report alongside
it. It never writes to existing saved user applications. It checks frontend build
and create/reload/edit/delete behavior in the isolated container. Reload is not
an application-restart persistence test; that remains a later explicit gate.

## Current boundary

The typed commerce specification is preparatory. Commerce generation remains
blocked until the PostgreSQL relational runtime and the subsequent phase gates
are implemented and verified. Do not use this change to claim a complete store.
