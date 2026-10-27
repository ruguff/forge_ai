# Section 2.4 Sequence diagrams

Open ProjectForge_UML_Sequence_Diagrams_A4.drawio (or the identical .xml file) in draw.io using File > Open From > Device. Switch between the three bottom page tabs. The matching PDF is prepared on A4 landscape pages with Times New Roman text.

## Figure 2.4(a) Project creation and clarification

The user submits an idea, the API creates a project and persists it, and the frontend requests understanding. The local model returns structured information through the understanding service. RequirementEngine evaluates readiness. Clarification repeats only when questions remain. Understanding may use explicitly labelled heuristic suggestions after model extraction fails; this does not mean specialist analysis succeeded.

## Figure 2.4(b) Offline specialists and build specification

The analyze endpoint schedules a background pipeline and returns started. The offline order is Product, AI/ML, Engineering, UX, Security, and QA. Each specialist uses its own execution harness with bounded validation retries. Saved outputs and progress are reported through callbacks and SSE. A conflict check and blueprint precede BuildSpec compilation. The compiler calls the local model for its sections and validates the result. The optional compilation region applies only when there are no unresolved conflicts. Any failed model/validation step stops the affected workflow; the diagram depicts the principal successful planning path rather than every exception handler.

The label Pipeline refers to _run_pipeline_background/run_specialists functions, not an invented Pipeline class. Specialist represents six successive instances, not a shared parent class. Local model groups LocalModelClient, LM Studio context checks, and inference for readability. No model-to-model discussion protocol is implied.

## Figure 2.4(c) Generation and verification

The frontend's autonomous mode starts the build after planning; a manual API request can also start it. Guided mode additionally requires approval before build, which is outside this autonomous scenario. The API runs CodingOrchestrator in a worker thread. Tasks generate authorized files in dependency order. Repository writes pass through AgentToolContext, omitted as a separate lifeline for space.

In the current offline DECLARATIVE_CRUD strategy, source is compiled deterministically from the AI-designed specification; each file is not another model inference. TestRunner executes actual backend, frontend, HTTP acceptance, and browser checks inside offline-network Docker containers. The alt fragment shows mutually exclusive outcome branches, not two reports returned during one run. The actual implementation may attempt bounded repairs for eligible backend test failures; this supporting subflow is omitted. VERIFIED requires all required checks to pass. BLOCKED/REQUIRES_HUMAN indicates unresolved conditions; unexpected exceptions can also produce FAILED and HTTP 500.

Final project status/report is persisted by the API before the HTTP response. Artifact files and detailed check results remain in the generated workspace. The diagrams do not imply that the generated website starts automatically after verification.

## Notation

- Actor: external user.
- Headed participant plus dashed vertical line: lifeline; time advances downward.
- Narrow rectangle: activation/execution occurrence.
- Solid filled arrow: call for which the caller awaits a result at this abstraction level.
- Open arrow: asynchronous background scheduling or SSE notification.
- Dashed open arrow: returned result.
- Self message: local conflict/blueprint operations, delegated helpers condensed.
- loop/opt/alt: iteration, conditional execution, and alternative outcomes.
- boundary/control/entity stereotypes classify participants; they do not introduce new Python classes.

Selected calls and returns are condensed for readability. Persistence operations are grouped where they form one logical event/save action. The XML and matching rendered geometry were generated programmatically and preview images were inspected; the file was not opened in the live draw.io editor during creation. Confirm text placement in draw.io before final report export.

Source references: backend/app/api/endpoints.py, backend/app/api/persistence.py, backend/app/agents/pipeline.py, backend/app/agents/understanding_service.py, backend/app/harness/base_harness.py, backend/app/execution/spec/local_compiler.py, backend/app/execution/orchestrator/coding_orchestrator.py, backend/app/execution/sandbox/test_runner.py, backend/app/execution/sandbox/executor.py, and frontend/src/context/OfficeContext.tsx.
