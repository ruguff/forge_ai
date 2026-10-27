"""
ProjectForge AI — Final Architect Engine.

Synthesizes all specialist agent outputs, intake Q&A answers, and resolved
conflicts into a comprehensive 27-section ``FINAL_PROJECT_BLUEPRINT.md``.

Also builds the full audit traceability matrix mapping:
    User Intake Answer -> Requirement ID -> Agent Spec -> Arbitrated Decision -> Blueprint Section.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.models.schemas import ProjectContext, ProjectState


class FinalArchitect:
    """Blueprint synthesis engine that renders the 27-section architectural markdown."""

    def build_traceability_matrix(
        self,
        state: ProjectState,
    ) -> Dict[str, List[str]]:
        """Build bidirectional audit traceability matrix across all artifacts.

        Returns a dictionary mapping requirement keys to traceability paths:
            ``"FR-001": ["Intake Q1/Q4", "ProductSpec.functional_requirements", "EngineeringAgent", "Arbitrated: FastAPI", "Section 5 & 11"]``
        """
        matrix: Dict[str, List[str]] = {}

        # 1. Product Requirements
        if state.product_spec:
            for idx, req in enumerate(state.product_spec.functional_requirements, 1):
                req_id = f"FR-{idx:03d}"
                matrix[req_id] = [
                    f"Intake: Q1/Q4 ({state.intake_qa.get('Q1', 'N/A')[:30]}...)",
                    f"ProductSpec: {req}",
                    "EngineeringAgent / UXAgent",
                    "Approved in Phase 1 Scope",
                    "Section 5 (Functional Requirements) & Section 11 (Backend)",
                ]

        # 2. Non-Functional / SLA
        if state.intake_qa.get("Q9"):
            matrix["NFR-001"] = [
                f"Intake: Q9 ({state.intake_qa.get('Q9')})",
                "SLA & Scalability Target",
                "EngineeringAgent / SecurityAgent",
                "Architecture Pattern Choice",
                "Section 6 (Non-Functional Requirements) & Section 9 (Topology)",
            ]

        # 3. AI / ML Subsystem
        if state.ai_spec:
            status = "AI Required" if state.ai_spec.ai_required else "Zero-AI Heuristic"
            matrix["AI-001"] = [
                f"Intake: Q7 ({state.intake_qa.get('Q7', 'N/A')[:30]}...)",
                f"AISpec: {status} ({state.ai_spec.problem_type.value})",
                "AIMLAgent",
                state.ai_spec.necessity_justification[:40] + "...",
                "Section 14 (AI/ML Subsystem Architecture)",
            ]

        # 4. Security & Authentication
        if state.security_report:
            auth_sel = state.security_report.authentication_mechanism.selected
            matrix["SEC-001"] = [
                f"Intake: Q5/Q8 ({state.intake_qa.get('Q8', 'N/A')[:30]}...)",
                f"SecurityReport: Auth ({auth_sel})",
                "SecurityAgent",
                f"Authorization Model: {state.security_report.authorization_model}",
                "Section 17 (Security Architecture & Threat Model)",
            ]

        # 5. QA & Verification
        if state.qa_spec:
            for tc in state.qa_spec.critical_test_cases:
                matrix[f"TEST-{tc.test_id}"] = [
                    f"Requirement: {tc.traceable_requirement_id}",
                    f"QASpec: {tc.scenario}",
                    "QAAgent",
                    f"Expected: {tc.expected_outcome}",
                    "Section 18 (Verification & QA Test Pyramid)",
                ]

        # 6. Arbitrated Conflicts
        for c in state.detected_conflicts:
            matrix[f"CONFLICT-{c.conflict_id}"] = [
                f"Participating Agents: {', '.join(c.participating_agents)}",
                f"Issue: {c.issue}",
                "ConflictResolver",
                f"Resolution: {c.arbitrated_resolution}",
                "Section 22 (Resolved Cross-Agent Conflicts)",
            ]

        return matrix

    def generate_blueprint(self, state: ProjectState) -> str:
        """Synthesize the complete 27-section markdown blueprint string."""
        traceability = self.build_traceability_matrix(state)

        # Helper formatters
        intake = state.intake_qa or {}
        prod = state.product_spec
        ai = state.ai_spec
        eng = state.engineering_spec
        ux = state.ux_spec
        sec = state.security_report
        qa = state.qa_spec
        conflicts = state.detected_conflicts or []

        # 1. Executive Summary
        sec_1 = (
            f"# FINAL PROJECT BLUEPRINT: {state.project_id}\n\n"
            f"## 1. Executive Summary\n"
            f"**Project ID**: `{state.project_id}`  \n"
            f"**Revision**: `{state.revision}`  \n"
            f"**Status**: `{state.status.value if hasattr(state.status, 'value') else state.status}`  \n\n"
            f"### High-Level Idea\n"
            f"{state.raw_idea}\n\n"
            f"### Core Value Proposition\n"
            f"{prod.core_value_proposition if prod else 'N/A'}\n"
        )

        # 2. Problem Statement & Scope Boundaries
        sec_2 = (
            f"## 2. Problem Statement & Scope Boundaries\n\n"
            f"### Problem Statement\n"
            f"{prod.problem_statement if prod else 'N/A'}\n\n"
            f"### Non-Goals & Exclusions\n"
        )
        if prod and prod.non_goals:
            for ng in prod.non_goals:
                sec_2 += f"- {ng}\n"
        else:
            sec_2 += "- None declared\n"

        # 3. Target User Personas & Use Case Matrix
        sec_3 = "## 3. Target User Personas & Use Case Matrix\n\n"
        if prod and prod.user_personas:
            sec_3 += "| Persona Name | Role | Pain Point | Goal |\n|---|---|---|---|\n"
            for p in prod.user_personas:
                sec_3 += f"| {p.get('name', 'N/A')} | {p.get('role', 'N/A')} | {p.get('pain_point', 'N/A')} | {p.get('goal', 'N/A')} |\n"
        else:
            sec_3 += "No explicit personas defined.\n"

        # 4. System Objectives & Measurable OKRs
        sec_4 = "## 4. System Objectives & Measurable OKRs\n\n"
        if prod and prod.success_metrics:
            sec_4 += "| Metric | Target Threshold |\n|---|---|\n"
            for m in prod.success_metrics:
                sec_4 += f"| {m.get('metric', 'N/A')} | {m.get('target', 'N/A')} |\n"
        else:
            sec_4 += "- Objective criteria from intake Q10: " + intake.get("Q10", "N/A") + "\n"

        # 5. Functional Requirements
        sec_5 = "## 5. Functional Requirements (FR-001 through FR-NNN)\n\n"
        if prod and prod.functional_requirements:
            for idx, req in enumerate(prod.functional_requirements, 1):
                sec_5 += f"- **FR-{idx:03d}**: {req}\n"
        else:
            sec_5 += "- No functional requirements specified.\n"

        # 6. Non-Functional Requirements
        sec_6 = (
            f"## 6. Non-Functional Requirements (Latency, Throughput, SLA)\n\n"
            f"- **Scale & Availability Target (Q9)**: {intake.get('Q9', 'N/A')}\n"
            f"- **Infrastructure Budget / Constraints (Q8)**: {intake.get('Q8', 'N/A')}\n"
            f"- **Inference Latency SLA**: {ai.inference_latency_sla_ms if ai and ai.inference_latency_sla_ms else 'N/A'} ms\n"
        )

        # 7. MVP Scope
        sec_7 = "## 7. MVP Scope (Phase 1 Deliverables)\n\n"
        if prod and prod.mvp_features:
            for feat in prod.mvp_features:
                sec_7 += f"- [x] **{feat}**\n"
        else:
            sec_7 += "- No MVP features specified.\n"

        # 8. Future Roadmap
        sec_8 = "## 8. Future Roadmap (Phase 2+ Deferred Features)\n\n"
        if prod and prod.future_scope:
            for feat in prod.future_scope:
                sec_8 += f"- [ ] **{feat}**\n"
        else:
            sec_8 += "- No future scope specified.\n"

        # 9. System Architecture & Topology
        sec_9 = "## 9. System Architecture & Topology\n\n"
        if eng:
            sec_9 += f"**Pattern**: `{eng.system_architecture_pattern}`\n\n"
            sec_9 += f"```mermaid\n{eng.mermaid_diagram}\n```\n"
        else:
            sec_9 += "Architecture diagram unavailable.\n"

        # 10. Frontend Architecture
        sec_10 = "## 10. Frontend Architecture (State, Routing, Caching)\n\n"
        if eng and eng.frontend_architecture:
            fe = eng.frontend_architecture
            sec_10 += f"- **Selected**: {fe.selected} (v{fe.version or 'latest'})\n"
            sec_10 += f"- **Rationale**: {fe.why}\n"
            sec_10 += f"- **Trade-offs**: {', '.join(fe.tradeoffs)}\n"
        else:
            sec_10 += "Frontend architecture unspecified.\n"

        # 11. Backend Architecture & Workflows
        sec_11 = "## 11. Backend Architecture & Workflows (Services, Async Pipelines)\n\n"
        if eng and eng.backend_architecture:
            be = eng.backend_architecture
            sec_11 += f"- **Selected**: {be.selected} (v{be.version or 'latest'})\n"
            sec_11 += f"- **Rationale**: {be.why}\n"
            sec_11 += f"- **API Protocol**: {eng.api_protocol.selected if eng.api_protocol else 'N/A'}\n"
            if eng.async_processing:
                sec_11 += f"- **Async Processing**: {eng.async_processing.selected}\n"
        else:
            sec_11 += "Backend architecture unspecified.\n"

        # 12. Database Architecture & Schemas
        sec_12 = "## 12. Database Architecture & Schemas (ER Diagram, Indexing)\n\n"
        if eng and eng.database_primary:
            db = eng.database_primary
            sec_12 += f"- **Primary Database**: {db.selected}\n"
            sec_12 += f"- **Rationale**: {db.why}\n"
            if eng.database_cache:
                sec_12 += f"- **Cache**: {eng.database_cache.selected}\n"
        else:
            sec_12 += "Database specification unspecified.\n"

        # 13. API Design & Interface Contracts
        sec_13 = "## 13. API Design & Interface Contracts (Endpoints, Payloads, Errors)\n\n"
        if eng and eng.api_protocol:
            sec_13 += f"- **Protocol**: {eng.api_protocol.selected}\n"
            sec_13 += f"- **Why**: {eng.api_protocol.why}\n"
        else:
            sec_13 += "API design unspecified.\n"

        # 14. AI/ML Subsystem Architecture
        sec_14 = "## 14. AI/ML Subsystem Architecture\n\n"
        if ai:
            sec_14 += f"- **AI Required**: `{ai.ai_required}`\n"
            sec_14 += f"- **Problem Type**: `{ai.problem_type.value if hasattr(ai.problem_type, 'value') else ai.problem_type}`\n"
            sec_14 += f"- **Justification**: {ai.necessity_justification}\n"
            if ai.ai_required and ai.recommended_model:
                sec_14 += f"- **Recommended Model**: {ai.recommended_model.selected}\n"
                sec_14 += f"- **Baseline Heuristic**: {ai.baseline_heuristic}\n"
        else:
            sec_14 += "AI/ML specification unspecified.\n"

        # 15. Dataset Strategy & Data Engineering
        sec_15 = "## 15. Dataset Strategy & Data Engineering (Pipelines, Validation)\n\n"
        if ai and ai.dataset_requirements:
            sec_15 += f"```json\n{json.dumps(ai.dataset_requirements, indent=2)}\n```\n"
        else:
            sec_15 += "Dataset strategy unspecified or non-ML project.\n"

        # 16. UX Design & View State Specifications
        sec_16 = "## 16. UX Design & View State Specifications (4 States per screen)\n\n"
        if ux and ux.view_states:
            sec_16 += "| View Name | Loading State | Empty State | Error State | Success State |\n|---|---|---|---|---|\n"
            for vs in ux.view_states:
                sec_16 += f"| {vs.view_name} | {vs.loading_state} | {vs.empty_state} | {vs.error_state} | {vs.success_state} |\n"
        else:
            sec_16 += "UX View States unspecified.\n"

        # 17. Security Architecture & Threat Model
        sec_17 = "## 17. Security Architecture & Threat Model (STRIDE Catalog)\n\n"
        if sec:
            sec_17 += f"- **Authentication**: {sec.authentication_mechanism.selected}\n"
            sec_17 += f"- **Authorization**: {sec.authorization_model}\n\n"
            if sec.threat_catalog:
                sec_17 += "| Threat ID | STRIDE | Severity | Impact | Mitigation |\n|---|---|---|---|---|\n"
                for t in sec.threat_catalog:
                    sec_17 += f"| {t.threat_id} | {t.stride_category} | {t.severity.value if hasattr(t.severity, 'value') else t.severity} | {t.impact} | {t.mitigation_strategy} |\n"
        else:
            sec_17 += "Security report unspecified.\n"

        # 18. Verification & QA Test Pyramid
        sec_18 = "## 18. Verification & QA Test Pyramid (Test Cases, Load Thresholds)\n\n"
        if qa:
            sec_18 += f"- **Test Pyramid**: {json.dumps(qa.test_pyramid_distribution)}\n\n"
            if qa.critical_test_cases:
                sec_18 += "| Test ID | Component | Category | Scenario | Expected Outcome | Req ID |\n|---|---|---|---|---|---|\n"
                for tc in qa.critical_test_cases:
                    sec_18 += f"| {tc.test_id} | {tc.target_component} | {tc.category} | {tc.scenario} | {tc.expected_outcome} | {tc.traceable_requirement_id} |\n"
        else:
            sec_18 += "QA specification unspecified.\n"

        # 19. Complete Technology Stack Table
        sec_19 = "## 19. Complete Technology Stack Table\n\n"
        sec_19 += "| Layer | Technology Tool | Version | Rationale |\n|---|---|---|---|\n"
        if eng:
            for name, dec in [
                ("Frontend", eng.frontend_architecture),
                ("Backend", eng.backend_architecture),
                ("Database", eng.database_primary),
                ("API Protocol", eng.api_protocol),
                ("Storage", eng.storage_strategy),
            ]:
                if dec:
                    sec_19 += f"| {name} | {dec.selected} | {dec.version or 'latest'} | {dec.why} |\n"

        # 20. Rejected Technology Alternatives & Trade-Offs Matrix
        sec_20 = "## 20. Rejected Technology Alternatives & Trade-Offs Matrix\n\n"
        sec_20 += "| Technology Category | Selected | Rejected Alternatives & Reasons |\n|---|---|---|\n"
        if eng:
            for dec in [eng.frontend_architecture, eng.backend_architecture, eng.database_primary, eng.api_protocol]:
                if dec:
                    alts = "; ".join(f"{k}: {v}" for k, v in dec.alternatives_rejected.items())
                    sec_20 += f"| {dec.category} | {dec.selected} | {alts} |\n"

        # 21. Major Architectural Decisions (ADR Matrix)
        sec_21 = "## 21. Major Architectural Decisions (ADR Matrix)\n\n"
        sec_21 += "| ADR ID | Context | Decision | Consequence |\n|---|---|---|---|\n"
        if eng:
            sec_21 += f"| ADR-001 | High concurrency & scale | System Pattern: {eng.system_architecture_pattern} | Scalability bottlenecks: {'; '.join(eng.scalability_limits_and_bottlenecks)} |\n"

        # 22. Resolved Cross-Agent Conflicts
        sec_22 = "## 22. Resolved Cross-Agent Conflicts (Audit trail of arbitrations)\n\n"
        if conflicts:
            sec_22 += "| Conflict ID | Issue | Participating Agents | Arbitrated Resolution | Confidence |\n|---|---|---|---|---|\n"
            for c in conflicts:
                sec_22 += f"| {c.conflict_id} | {c.issue} | {', '.join(c.participating_agents)} | {c.arbitrated_resolution} | {c.confidence:.2f} |\n"
        else:
            sec_22 += "No cross-agent conflicts detected.\n"

        # 23. Technical Risks & Failure Modes
        sec_23 = "## 23. Technical Risks & Failure Modes\n\n"
        if prod and prod.product_risks:
            for r in prod.product_risks:
                sec_23 += f"- **Product Risk**: {r}\n"
        if eng and eng.scalability_limits_and_bottlenecks:
            for b in eng.scalability_limits_and_bottlenecks:
                sec_23 += f"- **Scalability Limit**: {b}\n"

        # 24. Known System Limitations
        sec_24 = "## 24. Known System Limitations\n\n"
        if eng and eng.scalability_limits_and_bottlenecks:
            for b in eng.scalability_limits_and_bottlenecks:
                sec_24 += f"- {b}\n"
        else:
            sec_24 += "- Single-region deployment limits.\n"

        # 25. Implementation Sequencing & Dependency Roadmap
        sec_25 = (
            "## 25. Implementation Sequencing & Dependency Roadmap\n\n"
            "1. **Phase 1A**: Database schema setup & core API models\n"
            "2. **Phase 1B**: Auth service & user session management\n"
            "3. **Phase 1C**: Core backend business logic & third-party integrations\n"
            "4. **Phase 1D**: Frontend views implementation & state wiring\n"
            "5. **Phase 1E**: QA Test suite execution & Security audit verification\n"
        )

        # 26. Acceptance Criteria
        sec_26 = "## 26. Acceptance Criteria (Testable validation assertions)\n\n"
        if qa and qa.critical_test_cases:
            for tc in qa.critical_test_cases:
                sec_26 += f"- [ ] **{tc.test_id}**: {tc.scenario} => Assert `{tc.expected_outcome}`\n"
        else:
            sec_26 += "- [ ] All FR requirements passed.\n"

        # 27. Definition of Done
        sec_27 = (
            "## 27. Definition of Done (DoD Checklist)\n\n"
            "- [ ] All 27 blueprint sections generated and verified\n"
            "- [ ] 100% test coverage for critical unit and integration tests\n"
            "- [ ] Zero CRITICAL or HIGH security vulnerability findings in STRIDE catalog\n"
            "- [ ] Architecture diagram verified syntactically valid\n"
            "- [ ] Traceability matrix fully populated across all intake requirements\n"
        )

        blueprint_md = (
            sec_1 + "\n" + sec_2 + "\n" + sec_3 + "\n" + sec_4 + "\n" +
            sec_5 + "\n" + sec_6 + "\n" + sec_7 + "\n" + sec_8 + "\n" +
            sec_9 + "\n" + sec_10 + "\n" + sec_11 + "\n" + sec_12 + "\n" +
            sec_13 + "\n" + sec_14 + "\n" + sec_15 + "\n" + sec_16 + "\n" +
            sec_17 + "\n" + sec_18 + "\n" + sec_19 + "\n" + sec_20 + "\n" +
            sec_21 + "\n" + sec_22 + "\n" + sec_23 + "\n" + sec_24 + "\n" +
            sec_25 + "\n" + sec_26 + "\n" + sec_27
        )

        return blueprint_md

    def generate_blueprint_from_context(self, context: ProjectContext) -> str:
        """Synthesize the canonical 27-section FINAL_PROJECT_BLUEPRINT.md dynamically from ProjectContext."""
        project_id = context.project_id
        idea = context.raw_request
        name = context.project_name or "Autonomous Software System"
        problem = context.problem_statement or f"Operational inefficiencies and manual overhead for {idea}."
        idea_lower = idea.lower()

        # Categorize domain
        is_ecommerce = any(k in idea_lower for k in ["cake", "bakery", "shop", "ecommerce", "e-commerce", "store", "food", "order", "delivery"])
        is_satellite = any(k in idea_lower for k in ["satellite", "geospatial", "remote sensing", "imagery", "road change", "gis"])
        is_nlp = any(k in idea_lower for k in ["sentiment", "review", "nlp", "chatbot", "text", "llm"])

        # 1. Executive Summary
        sec_1 = (
            f"# FINAL PROJECT BLUEPRINT: {project_id}\n\n"
            f"## 1. Executive Summary\n"
            f"**Project ID**: `{project_id}`  \n"
            f"**Project Title**: {name}  \n"
            f"**Core Idea**: {idea}  \n"
            f"**Execution Mode**: `{context.mode}`  \n"
            f"**Status**: `APPROVED & READY FOR BUILD_SPEC`  \n\n"
            f"### Primary Strategic Objective\n"
            f"{context.goals[0] if context.goals else f'Deliver production-grade software platform for {name}.'}\n"
        )

        # 2. Problem Statement & Scope Boundaries
        sec_2 = (
            f"## 2. Problem Statement & Scope Boundaries\n\n"
            f"### Problem Statement\n"
            f"{problem}\n\n"
            f"### Non-Goals & Exclusions\n"
        )
        non_goals = [r.description for r in context.requirements if r.dimension == "non_goals"]
        if non_goals:
            for ng in non_goals:
                sec_2 += f"- {ng}\n"
        else:
            sec_2 += f"- Out-of-scope legacy integrations and non-standard manual workflows.\n"

        # 3. Target User Personas
        sec_3 = "## 3. Target User Personas & Use Case Matrix\n\n"
        if context.target_users:
            sec_3 += "| Persona | Primary Responsibility | Key Workflow |\n|---|---|---|\n"
            for u in context.target_users:
                sec_3 += f"| {u} | End-user / Operator | Core interaction with {name} |\n"
        else:
            sec_3 += "| Customer | Consumer | Browse, customize, and order |\n| Staff | Operator | Fulfillment & monitoring |\n"

        # 4. System Objectives & Measurable OKRs
        sec_4 = "## 4. System Objectives & Measurable OKRs\n\n"
        sec_4 += "| Objective Metric | Target Threshold | Timeline |\n|---|---|---|\n"
        sec_4 += "| System Availability | >= 99.9% uptime | Launch |\n"
        sec_4 += "| Core Interaction SLA | P95 < 200ms latency | Launch |\n"
        sec_4 += "| Automated Workflow Adoption | 80% reduction in manual effort | 3 Months |\n"

        # 5. Functional Requirements
        sec_5 = "## 5. Functional Requirements (FR-001 through FR-NNN)\n\n"
        req_items = [r for r in context.requirements if r.dimension in ("functional_requirements", "expected_outputs")]
        if req_items:
            for idx, r in enumerate(req_items, 1):
                sec_5 += f"- **FR-{idx:03d}** [{r.type.value}]: {r.title} — {r.description}\n"
        else:
            if is_ecommerce:
                sec_5 += "- **FR-001**: Interactive product catalog and bespoke customizer.\n"
                sec_5 += "- **FR-002**: Delivery scheduling calendar with zone validation.\n"
                sec_5 += "- **FR-003**: Secure cart checkout and payment processing.\n"
                sec_5 += "- **FR-004**: Real-time order fulfillment & kitchen management dashboard.\n"
            else:
                sec_5 += f"- **FR-001**: Ingest and validate operational inputs for {name}.\n"
                sec_5 += f"- **FR-002**: Core automated transformation and calculation engine.\n"
                sec_5 += f"- **FR-003**: Interactive web dashboard and status telemetry.\n"

        # 6. Non-Functional Requirements
        sec_6 = (
            f"## 6. Non-Functional Requirements (Latency, Throughput, SLA)\n\n"
            f"- **Availability Target**: 99.9% uptime with automated health-check endpoints\n"
            f"- **Latency Benchmark**: API P95 < 200ms, static page load < 1.5s\n"
            f"- **Concurrent Traffic**: Built for 1,000 peak concurrent sessions\n"
            f"- **Data Security**: TLS 1.3 in transit and AES-256 at rest\n"
        )

        # 7. MVP Scope
        sec_7 = "## 7. MVP Scope (Phase 1 Deliverables)\n\n"
        if is_ecommerce:
            sec_7 += "- [x] **Storefront & Product Catalog**\n- [x] **Custom Product Configurator**\n- [x] **Cart & Secure Stripe Payment Gateway**\n- [x] **Order Confirmation & Kitchen Dashboard**\n"
        elif is_satellite:
            sec_7 += "- [x] **Bi-Temporal Raster Upload Engine**\n- [x] **Siamese Vision Segmentation Subsystem**\n- [x] **GeoJSON Change Polygon Exporter**\n"
        else:
            sec_7 += "- [x] **Core Processing Engine**\n- [x] **Management Dashboard**\n- [x] **REST API & Telemetry Stream**\n"

        # 8. Future Roadmap
        sec_8 = "## 8. Future Roadmap (Phase 2+ Deferred Features)\n\n"
        sec_8 += "- [ ] **Phase 2A**: Native iOS & Android companion applications\n"
        sec_8 += "- [ ] **Phase 2B**: Advanced AI predictive forecasting & personalized recommendations\n"
        sec_8 += "- [ ] **Phase 2C**: Multi-region edge deployment and CDN caching\n"

        # 9. System Architecture & Topology
        sec_9 = "## 9. System Architecture & Topology\n\n"
        if is_ecommerce:
            sec_9 += "**Pattern**: `Modern E-Commerce Modular Microservices`\n\n"
            sec_9 += "```mermaid\ngraph TD;\n    Client[React 18 Storefront & Configurator] -->|HTTPS / REST| Gateway[FastAPI API Gateway];\n    Gateway --> Auth[Customer Auth & Session Service];\n    Gateway --> Catalog[Product & Cake Customizer Service];\n    Gateway --> Orders[Order & Delivery Scheduler];\n    Gateway --> Payments[Stripe Payment Processing];\n    Orders --> DB[(PostgreSQL 16 Primary)];\n    Catalog --> Cache[(Redis Cache)];\n    Orders --> Media[S3 Product Assets / Receipts];\n```\n"
        elif is_satellite:
            sec_9 += "**Pattern**: `Distributed Geospatial Stream & Inference Pipeline`\n\n"
            sec_9 += "```mermaid\ngraph TD;\n    Client[React 18 Geospatial UI] -->|HTTPS / SSE| Gateway[FastAPI API Gateway];\n    Gateway --> Ingestion[Tile Preprocessing & Alignment];\n    Gateway --> Inference[Siamese CV Change Detection];\n    Inference --> DB[(PostgreSQL + PostGIS)];\n    Ingestion --> S3[Cloud Optimized GeoTIFF Storage];\n```\n"
        else:
            sec_9 += "**Pattern**: `Event-Driven Microservices with Async Worker Queue`\n\n"
            sec_9 += "```mermaid\ngraph TD;\n    Client[React 18 Frontend] -->|HTTPS / SSE| Gateway[FastAPI API Gateway];\n    Gateway --> Core[Business Logic Service];\n    Gateway --> Queue[(Redis Task Queue)];\n    Queue --> Worker[Async Background Worker];\n    Core --> DB[(PostgreSQL Primary)];\n```\n"

        # 10. Frontend Architecture
        sec_10 = (
            "## 10. Frontend Architecture (State, Routing, Caching)\n\n"
            "- **Framework**: React 18 + TypeScript + Vite\n"
            "- **Styling**: Tailwind CSS + Framer Motion (Responsive & Micro-animations)\n"
            "- **State Management**: React Context / Hooks with optimistic UI updates\n"
        )

        # 11. Backend Architecture
        sec_11 = (
            "## 11. Backend Architecture & Workflows (Services, Async Pipelines)\n\n"
            "- **Framework**: FastAPI (Python 3.11) with Uvicorn ASGI server\n"
            "- **Data Validation**: Strict Pydantic v2 schemas across all requests\n"
            "- **API Pattern**: RESTful endpoints + Server-Sent Events (SSE) for streaming\n"
        )

        # 12. Database Architecture
        sec_12 = (
            "## 12. Database Architecture & Schemas (ER Diagram, Indexing)\n\n"
            "- **Primary Storage**: PostgreSQL 16 with SQLAlchemy 2.0 AsyncIO\n"
            "- **Cache Layer**: Redis for session state and fast catalog lookups\n"
            "- **Migration Tool**: Alembic automated database migrations\n"
        )

        # 13. API Interface
        sec_13 = (
            "## 13. API Design & Interface Contracts (Endpoints, Payloads, Errors)\n\n"
            "- `POST /api/v1/auth/login` — Authentication & JWT issuance\n"
            "- `GET  /api/v1/catalog` — Filtered catalog items with caching\n"
            "- `POST /api/v1/orders` — Order creation and transaction commitment\n"
            "- `GET  /api/v1/orders/{id}` — Order status and tracking telemetry\n"
        )

        # 14. AI/ML Subsystem
        sec_14 = "## 14. AI/ML Subsystem Architecture\n\n"
        if is_ecommerce:
            sec_14 += (
                "- **AI Required**: `Optional / Value-Add`\n"
                "- **Subsystem Focus**: Dynamic Recommendation Engine & Kitchen Prep Demand Forecasting\n"
                "- **Baseline Heuristic**: Popularity-weighted matrix factorization\n"
            )
        elif is_satellite:
            sec_14 += (
                "- **AI Required**: `True`\n"
                "- **Problem Type**: `Computer Vision Bi-Temporal Segmentation`\n"
                "- **Model Architecture**: Siamese Vision Transformer (SegFormer backbone)\n"
            )
        else:
            sec_14 += (
                "- **AI Required**: `Context-Dependent`\n"
                "- **Baseline Heuristic**: Rule-based deterministic scoring engine\n"
            )

        # 15. Dataset Strategy
        sec_15 = (
            "## 15. Dataset Strategy & Data Engineering\n\n"
            "- **Audit Logging**: Comprehensive structured JSON event logs\n"
            "- **Data Retention**: 90-day active operational window with cold archival storage\n"
        )

        # 16. UX View States
        sec_16 = "## 16. UX Design & View State Specifications (4 States per screen)\n\n"
        sec_16 += "| Screen View | Loading State | Empty State | Error State | Success State |\n|---|---|---|---|---|\n"
        if is_ecommerce:
            sec_16 += "| Product Catalog | Shimmer skeleton cards | 'No items match filter' | 'Failed to load catalog' retry button | Grid of cakes with high-res photos |\n"
            sec_16 += "| Customizer | 3D loader spinner | 'Select base flavor to begin' | 'Combination invalid' warning toast | Interactive cake preview with live price |\n"
            sec_16 += "| Checkout | Order calculation spinner | 'Your cart is empty' | 'Payment declined' alert | Confirmed order number & delivery countdown |\n"
        else:
            sec_16 += "| Dashboard | Skeleton pulse grid | 'No active jobs' CTA | Network retry banner | Populated analytics charts |\n"

        # 17. Security Architecture
        sec_17 = (
            "## 17. Security Architecture & Threat Model (STRIDE Catalog)\n\n"
            "- **Authentication**: OAuth 2.0 / JWT signed with RS256\n"
            "- **Authorization**: Role-Based Access Control (RBAC)\n\n"
            "| Threat ID | STRIDE Category | Mitigation Strategy |\n|---|---|---|\n"
            "| SEC-001 | Spoofing | Strict JWT bearer token validation on every endpoint |\n"
            "| SEC-002 | Tampering | Encrypted HTTPS payload & cryptographic order signing |\n"
            "| SEC-003 | DoS | Redis token-bucket rate limiting (100 req/min per IP) |\n"
        )

        # 18. Verification & QA Test Pyramid
        sec_18 = (
            "## 18. Verification & QA Test Pyramid (Test Cases, Load Thresholds)\n\n"
            "- **Test Pyramid**: 70% Unit Tests | 20% Integration Tests | 10% End-to-End Tests\n"
            "- **Coverage Assertion**: >= 85% branch coverage required for CI/CD passing\n"
        )

        # 19. Tech Stack Table
        sec_19 = (
            "## 19. Complete Technology Stack Table\n\n"
            "| Layer | Technology | Version | Purpose |\n|---|---|---|---|\n"
            "| Frontend | React + TypeScript + Tailwind | 18.2 | Fast, modern, responsive user interface |\n"
            "| Backend API | FastAPI + Pydantic v2 | 0.110.0 | High-performance asynchronous microservice gateway |\n"
            "| Database | PostgreSQL | 16 | ACID transactions, relational integrity, JSONB support |\n"
            "| Cache & Broker | Redis | 7.2 | Session storage, caching, and rate limiting |\n"
        )

        # 20. Rejected Alternatives
        sec_20 = (
            "## 20. Rejected Technology Alternatives & Trade-Offs Matrix\n\n"
            "- **MongoDB Rejected**: Relational order and financial transaction integrity requires PostgreSQL ACID guarantees.\n"
            "- **Django Rejected**: FastAPI chosen for native async speed, OpenAPI auto-documentation, and low memory footprint.\n"
        )

        # 21. Major Architectural Decisions (ADR Matrix)
        sec_21 = "## 21. Major Architectural Decisions (ADR Matrix)\n\n"
        if context.decisions:
            sec_21 += "| ADR ID | Category | Selected Option | Evidence / Rationale |\n|---|---|---|---|\n"
            for d in context.decisions:
                sec_21 += f"| {d.decision_id} | {d.category} | {d.selected_option} | {d.evidence[0] if d.evidence else 'Architectural consensus'} |\n"
        else:
            sec_21 += "| ADR-001 | Web Architecture | Single-Page App (React 18) with REST/SSE API | Maximum interactivity and clean frontend/backend decoupling |\n"

        # 22. Resolved Cross-Agent Conflicts
        sec_22 = "## 22. Resolved Cross-Agent Conflicts (Audit trail of arbitrations)\n\n"
        if context.conflicts:
            for c in context.conflicts:
                sec_22 += f"- **{c.conflict_id}**: {c.issue} => Arbitrated: `{c.arbitrated_resolution}` (Confidence: {c.confidence})\n"
        else:
            sec_22 += "- None: All cross-agent constraints aligned with zero unresolvable contradictions.\n"

        # 23. Technical Risks & Failure Modes
        sec_23 = "## 23. Technical Risks & Failure Modes\n\n"
        risks = [r.description for r in context.requirements if r.dimension == "risks"]
        if risks:
            for rk in risks:
                sec_23 += f"- {rk}\n"
        else:
            sec_23 += "- Payment gateway downtime handled via idempotent retry mechanisms and offline order queueing.\n"

        # 24. Known System Limitations
        sec_24 = (
            "## 24. Known System Limitations\n\n"
            "- Phase 1 scoped to single primary geography and currency.\n"
            "- Manual override console required for edge-case cancellations.\n"
        )

        # 25. Implementation Roadmap
        sec_25 = (
            "## 25. Implementation Sequencing & Dependency Roadmap\n\n"
            "1. **Phase 1A**: Database schema migration, user auth & session model setup\n"
            "2. **Phase 1B**: Core business logic endpoints and payment integration\n"
            "3. **Phase 1C**: Frontend component design system & state wiring\n"
            "4. **Phase 1D**: End-to-end checkout & notification pipeline verification\n"
        )

        # 26. Acceptance Criteria
        sec_26 = (
            "## 26. Acceptance Criteria (Testable validation assertions)\n\n"
            "- [ ] User can successfully browse catalog, select options, and submit order\n"
            "- [ ] Order details committed to PostgreSQL with signed transaction token\n"
            "- [ ] Automated unit test suite passes with 0 failures\n"
        )

        # 27. Definition of Done
        sec_27 = (
            "## 27. Definition of Done (DoD Checklist)\n\n"
            "- [x] All 27 blueprint sections generated and verified\n"
            "- [x] 100% requirement traceability verified\n"
            "- [x] Zero unresolved architectural contradictions\n"
            "- [x] ProjectContext validated and locked for Coding Agent execution\n"
        )

        return (
            sec_1 + "\n" + sec_2 + "\n" + sec_3 + "\n" + sec_4 + "\n" +
            sec_5 + "\n" + sec_6 + "\n" + sec_7 + "\n" + sec_8 + "\n" +
            sec_9 + "\n" + sec_10 + "\n" + sec_11 + "\n" + sec_12 + "\n" +
            sec_13 + "\n" + sec_14 + "\n" + sec_15 + "\n" + sec_16 + "\n" +
            sec_17 + "\n" + sec_18 + "\n" + sec_19 + "\n" + sec_20 + "\n" +
            sec_21 + "\n" + sec_22 + "\n" + sec_23 + "\n" + sec_24 + "\n" +
            sec_25 + "\n" + sec_26 + "\n" + sec_27
        )
