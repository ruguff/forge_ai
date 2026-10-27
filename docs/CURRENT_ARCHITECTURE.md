# CURRENT_ARCHITECTURE.md — PROJECTFORGE AI

---

## 1. Executive Architecture Overview

**PROJECTFORGE AI** is an AI-powered multi-agent software architecture system designed to transform a raw user project idea into a validated, canonical 27-section software architecture specification (`FINAL_PROJECT_BLUEPRINT.md`).

The codebase consists of:
- **Backend**: FastAPI 0.110.0 + Pydantic v2 + SQLAlchemy 2.0 (AsyncIO) / SQLite + Google GenAI SDK (`google-genai`).
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Framer Motion.
- **Orchestration**: `AgentExecutionHarness` wrapping 7 specialized agents (`Intake`, `Product`, `AI/ML`, `Engineering`, `UX`, `Security`, `QA`), plus a weighted multi-criteria `ConflictResolver` and `FinalArchitect`.

---

## 2. Existing System Components & File Map

### Backend Layout (`backend/app/`)
- `config.py`: Pydantic-settings configuration (`Settings` with `GEMINI_API_KEY`, `DATABASE_URL`, `EMBEDDING_MODEL`).
- `database.py`: Async SQLAlchemy engine (`async_sessionmaker`, `Base`, `init_db()`).
- `models/db_models.py`: SQLAlchemy ORM models (`ProjectDB`, `IntakeResponseDB`, `AgentRunDB`, `ConflictDB`, `BlueprintDB`).
- `models/schemas.py`: Pydantic v2 validation schemas (`ConfidenceScore`, `TechDecision`, `ProductSpecification`, `AIArchitectureSpecification`, `EngineeringSpecification`, `UXSpecification`, `SecurityReport`, `QASpecification`, `Conflict`, `ProjectState`).
- `harness/base_harness.py`: `AgentExecutionHarness` executing agent runs with JSON schema enforcement, diagnostic retries, deterministic linting rules, and confidence calibration.
- `harness/context_filter.py`: `ContextFilter` scoping state subsets to individual agents to prevent context bloat.
- `harness/calibration.py`: Empirical confidence calibration formula:
  $$C = \frac{E}{E + A} \times (1.0 - P_{\text{risk}})$$
- `agents/`:
  - `intake_agent.py`: Adaptive 10-question Q&A intake flow.
  - `product_agent.py`: MVP scope, user personas, non-goals, functional requirements.
  - `aiml_agent.py`: Task classification, RoBERTa/VADER models, dataset strategy.
  - `engineering_agent.py`: Microservices topology, technology decision alternatives (>=2 options), API protocols.
  - `ux_agent.py`: 4-state screen matrix (Loading, Empty, Error, Success), user journeys.
  - `security_agent.py`: STRIDE threat modeling, authentication, authorization policies.
  - `qa_agent.py`: Test pyramid ratios (Unit/Integration/E2E), requirement test case mapping.
  - `conflict_resolver.py`: 5 structural conflict detectors + weighted utility matrix arbitration ($U = \sum w_i \times s_i$).
  - `final_architect.py`: 27-section `FINAL_PROJECT_BLUEPRINT.md` master synthesis.
- `api/endpoints.py`: REST routes (`POST /api/intake`, `POST /api/run-pipeline`, `GET /api/events/{project_id}`) and SSE streaming.

### Frontend Layout (`frontend/src/`)
- `components/Navigation/TopNavigation.tsx`: 52px Linear/Raycast style top bar with 6-stage DAG stepper, project tags, and CTAs.
- `components/Navigation/LeftActivityRail.tsx`: 48px VS Code style vertical tool rail.
- `components/Navigation/StatusBar.tsx`: 28px Terminal status bar with engine telemetry and canvas zoom controls.
- `components/Spatial/SpatialWarRoom.tsx`: Architectural $24\text{px}$ dot grid canvas (`.bg-warroom-grid`) with CAD technical corner framing brackets.
- `components/Spatial/AgentAvatarPod.tsx`: $270\text{px}$ workstation pod cards displaying agent avatars, monitor screens (State, Confidence % meter), and output triggers.
- `components/Spatial/RadarMinimap.tsx`: $180\times 110\text{px}$ tactical radar minimap with active agent node highlights and camera viewport bounding box.
- `components/Office/DataFlowBeams.tsx`: Animated SVG DAG pipeline flow rays.
- `components/Blueprint/BlueprintViewer.tsx`: 27-section blueprint & requirement traceability matrix modal.
- `components/Conflicts/ConflictRoomPanel.tsx`: Interactive multi-criteria decision matrix arbitration viewer.

---

## 3. Current Agent Flow & Dependency Graph

```
USER
  │
  ▼
10-QUESTION INTAKE (IntakeAgent)
  │
  ▼
PROJECT CONTEXT STATE
  │
  ├──────────────────► PRODUCT AGENT (MVP, Personas, Non-Goals)
  │                      │
  ├──────────────────► AI/ML AGENT (Model Selection, Dataset Strategy)
  │                      │
  └──────────────────► ENGINEERING AGENT (Topology, Tech Stack)
                         │
                         ├────────► UX AGENT (4-State Views, Journeys)
                         │
                         ├────────► SECURITY AGENT (STRIDE Threat Model)
                         │
                         └────────► QA AGENT (Test Pyramid, Case Mapping)
                                       │
                                       ▼
                             CONFLICT RESOLVER (Detect & Arbitrate)
                                       │
                                       ▼
                             FINAL ARCHITECT (27-Section Synthesis)
```

---

## 4. Current Data Flow & API Contracts

1. `POST /api/intake/start`: Initializes `ProjectState`, runs question 1 of intake flow.
2. `POST /api/intake/answer`: Receives user answers, computes adaptive next question, completes intake after 10 questions.
3. `POST /api/pipeline/run`: Executes specialist agent pipeline sequentially/parallelly, filters context via `ContextFilter`, calibrates confidence, runs `ConflictResolver` arbitration matrix, and synthesizes `FINAL_PROJECT_BLUEPRINT.md`.
4. `GET /api/events/{project_id}`: Streams real-time SSE execution events to the frontend.

---

## 5. Existing Weaknesses & Limitations

1. **Agents Act as Linear LLM Invokers**: While wrapped in a harness, agents lack formal explicit **AgentContracts** defining explicit assumptions, failure conditions, tools, and acceptance criteria.
2. **Missing Real Coding Sandbox & Execution Loop**: System generates architectural specifications, but lacks an isolated **Coding Sandbox** (Docker/isolated workspace) to apply `BUILD_SPEC`, run real unit/integration tests, and perform iterative fix loops.
3. **No Quantitative Evaluation Benchmark**: Agent performance is validated via unit test assertions, but lacks an explicit quantitative internal evaluation engine (`Completeness`, `Correctness`, `Evidence Quality`, `Constraint Compliance`) and a benchmark suite of Golden Projects.
4. **Model Abstraction Bound to Cloud Gemini**: LLM invocation is currently tied to `google-genai` SDK without a decoupled `ModelProvider` layer supporting local open-weight models (Ollama, vLLM, local OpenAI-compatible endpoints).
5. **Lack of Browser-Based Visual QA Automation**: Web application verification currently relies on text-based test case mapping rather than automated Playwright browser execution and visual design reviews.

---

## 6. Real-World Transformation Plan & Roadmap

To transform PROJECTFORGE AI into a real, testable, evidence-driven multi-agent engineering system without rewriting existing code, we will execute the following incremental 16-step roadmap:

| Step | Phase | Core Objective | Key Files Impacted |
|---|---|---|---|
| 1 | Phase 1 & 2 | **Agent Contract System & Structured Artifacts** | `app/harness/contract.py`, `app/models/schemas.py` |
| 2 | Phase 3 & 4 | **Evidence Engine & SOP-Based Specialist Agents** | `app/harness/evidence.py`, `app/agents/*.py` |
| 3 | Phase 5 | **Dependency-Aware Dynamic Orchestrator** | `app/orchestrator/pipeline_orchestrator.py` |
| 4 | Phase 6 & 7 | **Agent Disagreement & Weighted Decision Matrix** | `app/agents/conflict_resolver.py` |
| 5 | Phase 8 & 9 | **Final Architecture Traceability Matrix** | `app/agents/final_architect.py` |
| 6 | Phase 10 & 11 | **Quantitative Evaluation Engine & Golden Benchmarks** | `app/evaluation/`, `evaluation/golden_projects/` |
| 7 | Phase 12 & 14 | **AI/ML Specialization & ModelProvider Abstraction** | `app/providers/model_provider.py` |
| 8 | Phase 13 & 15 | **Real Coding Agent & Isolated Workspace Sandbox** | `app/coding/coding_agent.py`, `app/coding/sandbox.py` |
| 9 | Phase 16 & 20 | **gstack-Inspired Workflow & Automated Fix Loop** | `app/workflows/fix_loop.py` |
| 10 | Phase 17 & 18 | **Browser QA & Design Review Engine** | `app/qa/browser_qa.py` |
| 11 | Phase 19 & 21 | **Security Review & Project Memory System** | `app/security/security_review.py`, `app/memory/` |
| 12 | Phase 22 & 23 | **Real Backend Event Stream to Office Visual UI** | `app/api/endpoints.py`, `frontend/src/` |
| 13 | Phase 24 & 25 | **Execution Trace Viewer & Telemetry Cost Tracker** | `app/observability/trace_viewer.py` |
| 14 | Phase 26 & 29 | **Failure Recovery & Prompt Injection Protection** | `app/harness/security_guardrails.py` |
| 15 | Phase 27 & 28 | **Full REST API Registry & Database Persistence** | `app/api/endpoints.py`, `app/models/db_models.py` |
| 16 | Phase 30 & 33 | **Comprehensive E2E Test Suite & Documentation** | `tests/`, `docs/` |

---

## 7. File Preservation Matrix

### Files That MUST Change (Evolve & Extend)
- `backend/app/harness/base_harness.py`: Extend to support `AgentContract` & SOP execution pipeline.
- `backend/app/models/schemas.py`: Add `AgentContract`, `EvidenceRecord`, `EvaluationResult`, `BuildSpec`.
- `backend/app/agents/*.py`: Update all 7 specialist agents, `ConflictResolver`, and `FinalArchitect` to produce structured artifacts with evidence chains.
- `backend/app/api/endpoints.py`: Add contract, evaluation, trace, and build endpoints.
- `frontend/src/App.tsx` & components: Connect real event telemetry stream and trace inspection capabilities.

### Files That MUST NOT Change (Preserve Core System)
- `backend/app/config.py`: Maintain environment configuration schema.
- `backend/app/database.py`: Maintain async SQLAlchemy initialization patterns.
- `backend/app/harness/calibration.py`: Preserve the empirical confidence calibration formula.
- `frontend/src/index.css`: Preserve `.bg-warroom-grid` and `.cad-corner-*` styling tokens.

---

## 8. First Implementation Milestone: Agent Contract System & Structured Artifacts

- Implement `backend/app/harness/contract.py` defining `AgentContract`.
- Implement `backend/app/harness/evidence.py` categorizing `FACT`, `INFERENCE`, `ASSUMPTION`, `RECOMMENDATION`, `UNKNOWN`.
- Create unit tests in `backend/tests/test_contracts.py`.
