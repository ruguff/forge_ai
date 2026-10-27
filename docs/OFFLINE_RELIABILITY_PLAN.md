# ProjectForge offline reliability plan

Prepared October 5, 2026. Planned work session: October 6, 2026 (Asia/Calcutta).

## Latest evidence — October 15, 2026

The saved diagnostic notes project PROJ-FCC520C200D2 now reports VERIFIED in docs/offline-build-report.json. All 11 files were compiled using DECLARATIVE_CRUD; backend tests, frontend build, API acceptance, and the three declared browser journeys passed in offline-network Docker containers. This replay used a previously saved model-designed specification and made zero new inference calls. It is not a fresh end-to-end six-agent run or an internet-disconnected inference test.

Fixed literal database defaults, moved Vite's cache out of read-only dependencies, and bound row Edit/Delete classes to the declared browser controls. Browser failures now include console/runtime/request diagnostics. Backend regression suite: 198 passed. Fresh workflow execution, stronger deletion/persistence assertions, and visual/performance inspection remain outstanding; the full plan is not complete.

## Goal

Complete one small website project through real local requirement extraction, six specialist agents, a validated build specification, generated source, and executable verification. Report each stage honestly; an isolated agent pass is not an end-to-end success.

## Verified starting point

- LM Studio serves `nvidia/nemotron-3-nano-4b` locally, with an 8192-token loaded context and one concurrent prediction.
- ProjectForge requests up to 4096 output tokens with `LOCAL_MODEL_REASONING_EFFORT=none`; input guard is 12000 characters and request timeout is 240 seconds.
- Engineering replay passed schema and lint on its first attempt: 92.2 seconds, 2574 input tokens, 1421 output tokens.
- Requirement extraction passed on its first attempt: 213.5 seconds, 1519 input tokens, 3262 output tokens.
- Backend regression suite: 174 passed. The latest pasted HTTP 500 came from an old process rejecting a new environment setting; restarting the updated backend resolved it.
- All six agents, compilation, code generation, and website verification have not yet passed together. Docker was previously unavailable; check its current availability before promising executable verification.

## Implementation order

### 1. Establish the current baseline

- Check backend, frontend, LM Studio, loaded context, concurrency, available memory, and Docker/image availability. Read only the necessary non-secret configuration values.
- Record a repeatable small notes-app brief: create, list, edit and delete notes; persist locally; React/TypeScript, FastAPI, SQLite; no login, external services or AI features in the generated app.
- Run a fresh project through analysis and capture per-stage duration, attempts, token usage, validation failures and fallback status. Preserve the failed state and completed outputs for diagnosis.
- Stop at the first actionable failure and fix that cause before rerunning expensive stages. Avoid concurrent diagnostic requests on this laptop.

### 2. Make request and retry limits reliable

- Fix recursive retry growth: retain the original instructions and only the latest response/diagnostics, rather than embedding every earlier attempt.
- Distinguish input-size rejection, output truncation, context overflow, timeout, invalid JSON and domain-validation failure in logs and UI events.
- Check loaded context through the local runtime. Use accurate runtime token counting if supported; otherwise label estimates and retain a conservative margin. Character limits must not be presented as exact token limits.
- Bound output to the available context and use measured stage duration to choose timeouts. Do not blindly increase limits to 40000 tokens or repeatedly retry unchanged truncated requests.
- Keep model calls local, sequential, bounded and cancellable. Preserve strict validation and explicitly labelled fallback behavior.

### 3. Split only stages that demonstrate a size problem

- Use baseline evidence to identify oversized schemas or responses.
- Split those stages into coherent sections, retaining relevant requirements and shared decisions. For example: frontend, backend, persistence, then integration for Engineering.
- Validate each section, merge deterministically, then validate the complete existing output schema and cross-section consistency. Do not relax requirements to obtain a green status.
- Keep original requirement IDs and provenance through every section. Do not summarize away user constraints.
- If resume support is needed, reuse completed artifacts only when requirement version, dependencies and relevant configuration still match; invalidate downstream artifacts after changes.

### 4. Complete planning and source generation

- Confirm all six specialists finish and inspect contradictions, unsupported technologies and invented requirements.
- Resolve genuine contradictions visibly before compiling the build specification.
- Generate source in bounded file tasks using the validated specification and relevant dependencies. Keep source containment and protected test contracts intact.
- Verify failure and blocked states reach the UI and no agent remains falsely marked working.

### 5. Verify the generated website

- If Docker and the required image are available, run the isolated backend/API checks, frontend build and browser acceptance tests.
- If unavailable, treat isolated execution as a prerequisite to address; do not substitute unrestricted host execution or label the website verified.
- Test create, edit, delete and persistence behavior against the original brief. Check the generated UI manually for obvious usability problems.
- Perform an internet-disconnected application test when the necessary model, runtime, image and dependencies are already installed. Confirm local inference and absence of cloud fallback.

### 6. Prepare the demonstration

- Document exact startup commands, prerequisites, expected waiting times, failure recovery and a repeatable demo brief.
- Save actual run evidence and known limitations. Keep frontend redesign outside this reliability session unless a UI defect prevents testing or misreports status.

## Completion criteria

- The fixed demonstration brief completes through all required stages with real outputs.
- Requirement extraction uses the local model; fallback use is visible and does not count as proof of successful model extraction.
- Generated code passes the required build, API and browser checks; blocked execution remains blocked until its prerequisites are met.
- Failures identify the affected stage and useful cause; retries stay bounded.
- Relevant regression tests pass and measured timing/resource constraints are documented.

## Tomorrow's first action

Inspect current services and prerequisites, then run the fixed notes-app brief once. Use the resulting evidence to choose the first code change. Keep the current 4096-token output setting unless measured results justify changing it.

This document is a work plan, not a scheduled task. No automatic run or reminder has been created.

## Status on October 14, 2026

The plan is NOT complete. Code and diagnostic checks progressed; final executable verification is blocked by Windows setup.

Completed:
- Fixed recursive retry growth and stopped unchanged truncation retries.
- Added real loaded-model token counting and context guards; kept 8192 context and 4096 output settings.
- Split Security, QA and build-spec compilation into bounded validated sections.
- Preserved requirement IDs/provenance by copying them directly rather than asking the model to recreate them.
- Fixed cyclic graph validation, unsafe file metadata, invalid browser navigation/selectors, missing mutation request data and missing post-interaction assertions.
- Fixed scheduler failure handling so incomplete generation cannot proceed as code complete.
- Investigated actual Nemotron source failures and introduced explicit DECLARATIVE_CRUD source compilation for the supported offline scope. This is a documented strategy change, not unrestricted AI code synthesis.
- Generated 11 source files from the validated model-designed notes specification. Static frontend types passed. Backend regression suite reached 194 passing tests.

Still required:
- Restart Windows to activate the enabled WSL/VirtualMachinePlatform features.
- Finish the official Docker download, verify its signature and install/start Docker.
- Build the trusted runtime image, then run the generated backend, API, frontend-build and browser checks inside it.
- Run a fresh complete public-API workflow and an internet-disconnected application test. Fix any runtime failures revealed by those checks.
- Inspect the generated running interface. No runtime success, browser success or frame-rate claim has been made.

Evidence: `offline-baseline.json`, `offline-continuation.json`, `offline-build-report.json`, `generated-static-types.json`, `sandbox-setup-status.json`. Diagnostic outputs do not overwrite the original live project's stopped status. The generated workspace is `backend/generated_projects/PROJ-FCC520C200D2/offline-reliability-v2`.
