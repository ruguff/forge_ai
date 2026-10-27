"""
ProjectForge AI — Conflict Arbitration & Blueprint Verification Tests.

Covers:
  - ConflictResolver.detect_conflicts: detecting intentional structural contradictions
    (AI vs deterministic engineering, protocol, DB, Security vs UX, Latency vs Budget)
  - ConflictResolver.resolve_conflict: weighted decision matrix utility computation,
    confidence calculation, and arbitration output
  - FinalArchitect.generate_blueprint: generating a Markdown string with all 27 canonical section headers
  - FinalArchitect.build_traceability_matrix: bidirectional requirement mapping
"""

from __future__ import annotations

import pytest
from typing import Any, Dict

from app.agents.conflict_resolver import (
    CRITERIA_WEIGHTS,
    ConflictResolver,
    compute_weighted_utility,
)
from app.agents.final_architect import FinalArchitect
from app.models.schemas import (
    AIArchitectureSpecification,
    ConfidenceScore,
    Conflict,
    EngineeringSpecification,
    ProblemType,
    ProductSpecification,
    ProjectState,
    ProjectStatus,
    QASpecification,
    SecurityReport,
    SecurityThreat,
    SeverityLevel,
    TechDecision,
    TestCase,
    UXSpecification,
    ViewStateSpecification,
)


def _make_confidence(**overrides) -> ConfidenceScore:
    base = {
        "score": 0.90,
        "fact_references": ["RFC-2119", "ISO-27001"],
        "unverified_assumptions": ["Low user concurrency at launch"],
        "risk_penalty": 0.1,
        "justification": "Grounded in standard industry references.",
    }
    base.update(overrides)
    return ConfidenceScore(**base)


def _make_tech_decision(**overrides) -> TechDecision:
    base = {
        "category": "Backend Framework",
        "selected": "FastAPI",
        "version": "0.110.0",
        "why": "High performance async framework",
        "alternatives_rejected": {
            "Django": "Too heavyweight",
            "Flask": "Lacks native async support",
        },
        "tradeoffs": ["Smaller ecosystem"],
        "failure_conditions": ["High CPU-bound tasks"],
        "confidence": _make_confidence(),
    }
    base.update(overrides)
    return TechDecision(**base)


def _make_sample_project_state() -> ProjectState:
    """Build a complete ProjectState for testing arbitration and blueprint generation."""
    return ProjectState(
        project_id="PROJ-ARBITRATION-TEST",
        revision=1,
        status=ProjectStatus.ARCHITECTING,
        raw_idea="AI-Powered Customer Feedback Sentiment Analyzer",
        intake_qa={
            "Q1": "Analyze customer review sentiment",
            "Q2": "Product Managers & Support teams",
            "Q3": "Upload CSV -> AI Processing -> Sentiment Dashboard",
            "Q4": "Sentiment Analysis, Keyword Extraction, Dashboard",
            "Q5": "CSV, JSON, REST API payloads",
            "Q6": "Sentiment reports, Trend charts",
            "Q7": "Probabilistic NLP/LLM sentiment scoring",
            "Q8": "Minimal infrastructure budget ($200/mo)",
            "Q9": "99.9% availability, SLA < 100ms",
            "Q10": "Reduce review triage time by 50%",
        },
        product_spec=ProductSpecification(
            problem_statement="Manual review analysis is slow and error-prone.",
            target_users=["Product Managers", "Support Team Leads"],
            user_personas=[
                {"name": "Sarah", "role": "PM", "pain_point": "Manual reading", "goal": "Automated sentiment"}
            ],
            core_value_proposition="Real-time sentiment insights for customer feedback.",
            functional_requirements=[
                "Upload feedback via CSV",
                "Automated NLP sentiment classification",
                "Real-time analytics dashboard",
            ],
            mvp_features=["CSV Upload", "Sentiment Classification", "Dashboard"],
            future_scope=["Multi-language support", "Slack Integration"],
            non_goals=["Automated customer response generation"],
            success_metrics=[{"metric": "Triage Speed", "target": "Reduce time by 50%"}],
            product_risks=["API rate limits", "Inaccurate sentiment scoring"],
        ),
        ai_spec=AIArchitectureSpecification(
            ai_required=True,
            necessity_justification="NLP model required to extract nuance from unstructured reviews.",
            problem_type=ProblemType.NLP_LLM,
            problem_formulation="Multi-class sentiment classification (Positive, Negative, Neutral)",
            candidate_models=[
                _make_tech_decision(category="LLM", selected="RoBERTa-fine-tuned"),
                _make_tech_decision(category="LLM", selected="GPT-4o-mini"),
            ],
            recommended_model=_make_tech_decision(category="LLM", selected="RoBERTa-fine-tuned"),
            dataset_requirements={"size": "50k reviews"},
            training_vs_api_strategy="API-based fine-tuned endpoint",
            inference_latency_sla_ms=50,
            evaluation_metrics=["Macro F1", "Accuracy"],
            baseline_heuristic="VADER Lexicon Classifier",
            compute_and_cost_estimation={"monthly": "$500"},
            hallucination_and_drift_mitigation=["Confidence thresholding"],
        ),
        engineering_spec=EngineeringSpecification(
            system_architecture_pattern="Microservices with Event Stream",
            frontend_architecture=_make_tech_decision(category="Frontend", selected="React", version="18.2"),
            backend_architecture=_make_tech_decision(category="Backend", selected="FastAPI", version="0.110.0"),
            database_primary=_make_tech_decision(category="Database", selected="PostgreSQL", version="16"),
            api_protocol=_make_tech_decision(category="API Protocol", selected="REST"),
            storage_strategy=_make_tech_decision(category="Storage", selected="AWS S3"),
            observability_stack={"logging": "Datadog", "metrics": "Prometheus", "tracing": "Jaeger"},
            mermaid_diagram="graph TD;\n  UI[React UI] --> API[FastAPI Backend];\n  API --> DB[(PostgreSQL)];",
            scalability_limits_and_bottlenecks=[
                "DB Write bottleneck at 5000 QPS",
                "S3 upload throughput limits",
            ],
        ),
        ux_spec=UXSpecification(
            primary_user_journey=["Login", "Upload CSV", "View Sentiment Dashboard"],
            information_architecture={"Dashboard": ["Summary", "Trends", "Raw Data"]},
            view_states=[
                ViewStateSpecification(
                    view_name="Dashboard",
                    loading_state="Skeleton cards",
                    empty_state="Upload prompt",
                    error_state="Error banner",
                    success_state="Charts and table grid",
                )
            ],
            accessibility_standards=["WCAG 2.1 AA"],
            responsive_breakpoints={"mobile": "480px", "tablet": "768px", "desktop": "1024px"},
        ),
        security_report=SecurityReport(
            authentication_mechanism=_make_tech_decision(category="Auth", selected="OAuth2 + OIDC"),
            authorization_model="Role-Based Access Control (RBAC)",
            data_protection_at_rest="AES-256",
            data_protection_in_transit="TLS 1.3",
            input_validation_rules=["Sanitize string inputs", "CSV payload validation"],
            threat_catalog=[
                SecurityThreat(
                    threat_id="SEC-001",
                    stride_category="Spoofing",
                    threat_description="Unauthorized API Access",
                    severity=SeverityLevel.HIGH,
                    impact="Data exposure",
                    likelihood=SeverityLevel.MEDIUM,
                    mitigation_strategy="Validate JWT tokens on every request",
                    priority=1,
                ),
                SecurityThreat(
                    threat_id="SEC-002",
                    stride_category="Tampering",
                    threat_description="CSV injection attack",
                    severity=SeverityLevel.HIGH,
                    impact="Malicious payload execution",
                    likelihood=SeverityLevel.LOW,
                    mitigation_strategy="Strict CSV parsing and cell sanitization",
                    priority=2,
                ),
                SecurityThreat(
                    threat_id="SEC-003",
                    stride_category="Denial of Service",
                    threat_description="Large payload flood",
                    severity=SeverityLevel.MEDIUM,
                    impact="Service slowdown",
                    likelihood=SeverityLevel.MEDIUM,
                    mitigation_strategy="Rate limiting and max payload cap",
                    priority=3,
                ),
            ],
        ),
        qa_spec=QASpecification(
            test_pyramid_distribution={"unit": "70%", "integration": "20%", "e2e": "10%"},
            frameworks_and_tooling=[_make_tech_decision(category="Test Tool", selected="PyTest")],
            critical_test_cases=[
                TestCase(
                    test_id="TC-001",
                    target_component="SentimentEngine",
                    category="unit",
                    scenario="Analyze positive review text",
                    expected_outcome="Sentiment score > 0.8",
                    traceable_requirement_id="FR-002",
                ),
                TestCase(
                    test_id="TC-002",
                    target_component="CSVParser",
                    category="unit",
                    scenario="Parse valid CSV file",
                    expected_outcome="Returns list of review objects",
                    traceable_requirement_id="FR-001",
                ),
                TestCase(
                    test_id="TC-003",
                    target_component="API Gateway",
                    category="integration",
                    scenario="Unauthorized request without token",
                    expected_outcome="401 Unauthorized status code",
                    traceable_requirement_id="SEC-001",
                ),
            ],
            performance_load_thresholds={"p99_latency": "200ms", "rps": "500"},
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFLICT DETECTOR TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestConflictDetector:
    def test_detect_ai_necessity_conflict(self):
        """Test detection of contradiction between AI recommendation and Engineering regex/static backend."""
        state = _make_sample_project_state()
        state_dict = state.model_dump()

        # Inject contradiction: Engineering specifies static regex rule engine backend
        state_dict["engineering_spec"]["backend_architecture"]["selected"] = "Static Regex Rule Engine"

        resolver = ConflictResolver()
        conflicts = resolver.detect_conflicts(state_dict)

        ai_conflicts = [c for c in conflicts if c.conflict_id == "CONFLICT-AI-001"]
        assert len(ai_conflicts) == 1
        assert "AIMLAgent" in ai_conflicts[0].participating_agents
        assert "EngineeringAgent" in ai_conflicts[0].participating_agents

    def test_detect_protocol_conflict(self):
        """Test detection of REST API specified by Engineering vs low SLA (<100ms) required by AI."""
        state = _make_sample_project_state()
        state_dict = state.model_dump()

        # Engineering specifies REST, AI inference SLA is 50ms (< 100ms)
        resolver = ConflictResolver()
        conflicts = resolver.detect_conflicts(state_dict)

        proto_conflicts = [c for c in conflicts if c.conflict_id == "CONFLICT-PROTO-001"]
        assert len(proto_conflicts) == 1
        assert "EngineeringAgent" in proto_conflicts[0].participating_agents

    def test_detect_latency_budget_conflict(self):
        """Test detection of high-performance latency SLA (<200ms) vs tight budget ($200/mo vs $500/mo cost)."""
        state = _make_sample_project_state()
        state_dict = state.model_dump()

        resolver = ConflictResolver()
        conflicts = resolver.detect_conflicts(state_dict)

        cost_conflicts = [c for c in conflicts if c.conflict_id == "CONFLICT-COST-001"]
        assert len(cost_conflicts) == 1
        assert "AIMLAgent" in cost_conflicts[0].participating_agents


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONFLICT ARBITRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestConflictArbitration:
    def test_weighted_utility_calculation(self):
        scores = {
            "maintainability": 8.0,
            "latency_performance": 9.0,
            "implementation_complexity": 7.0,
            "infrastructure_cost": 6.0,
            "scalability": 9.0,
        }
        # U = (0.25*8) + (0.20*9) + (0.20*7) + (0.20*6) + (0.15*9)
        #   = 2.0 + 1.8 + 1.4 + 1.2 + 1.35 = 7.75
        utility = compute_weighted_utility(scores)
        assert utility == pytest.approx(7.75)

    def test_resolve_conflict_utility_and_confidence(self):
        resolver = ConflictResolver()
        conflict = Conflict(
            conflict_id="CONFLICT-TEST-001",
            issue="Database choice contradiction",
            participating_agents=["EngineeringAgent", "AIMLAgent"],
            conflicting_recommendations={
                "EngineeringAgent": "Use PostgreSQL",
                "AIMLAgent": "Use Neo4j Graph DB",
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )

        option_a_scores = {
            "maintainability": 9.0,
            "latency_performance": 8.0,
            "implementation_complexity": 8.0,
            "infrastructure_cost": 9.0,
            "scalability": 8.0,
        }
        # Utility A = (0.25*9) + (0.2*8) + (0.2*8) + (0.2*9) + (0.15*8) = 2.25+1.6+1.6+1.8+1.2 = 8.45

        option_b_scores = {
            "maintainability": 5.0,
            "latency_performance": 7.0,
            "implementation_complexity": 4.0,
            "infrastructure_cost": 4.0,
            "scalability": 6.0,
        }
        # Utility B = (0.25*5) + (0.2*7) + (0.2*4) + (0.2*4) + (0.15*6) = 1.25+1.4+0.8+0.8+0.9 = 5.15

        resolved = resolver.resolve_conflict(
            conflict=conflict,
            project_constraints={},
            option_a_scores=option_a_scores,
            option_b_scores=option_b_scores,
        )

        assert "EngineeringAgent" in resolved.arbitrated_resolution
        assert resolved.confidence > 0.5
        assert len(resolved.compromise_penalties) > 0
        assert "EngineeringAgent" in resolved.evaluation_criteria_scores


# ══════════════════════════════════════════════════════════════════════════════
# 3. FINAL ARCHITECT BLUEPRINT GENERATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestFinalArchitect:
    def test_generate_blueprint_contains_all_27_sections(self):
        state = _make_sample_project_state()
        architect = FinalArchitect()
        blueprint = architect.generate_blueprint(state)

        # Expected 27 section titles
        expected_sections = [
            "## 1. Executive Summary",
            "## 2. Problem Statement & Scope Boundaries",
            "## 3. Target User Personas & Use Case Matrix",
            "## 4. System Objectives & Measurable OKRs",
            "## 5. Functional Requirements (FR-001 through FR-NNN)",
            "## 6. Non-Functional Requirements (Latency, Throughput, SLA)",
            "## 7. MVP Scope (Phase 1 Deliverables)",
            "## 8. Future Roadmap (Phase 2+ Deferred Features)",
            "## 9. System Architecture & Topology",
            "## 10. Frontend Architecture (State, Routing, Caching)",
            "## 11. Backend Architecture & Workflows (Services, Async Pipelines)",
            "## 12. Database Architecture & Schemas (ER Diagram, Indexing)",
            "## 13. API Design & Interface Contracts (Endpoints, Payloads, Errors)",
            "## 14. AI/ML Subsystem Architecture",
            "## 15. Dataset Strategy & Data Engineering (Pipelines, Validation)",
            "## 16. UX Design & View State Specifications (4 States per screen)",
            "## 17. Security Architecture & Threat Model (STRIDE Catalog)",
            "## 18. Verification & QA Test Pyramid (Test Cases, Load Thresholds)",
            "## 19. Complete Technology Stack Table",
            "## 20. Rejected Technology Alternatives & Trade-Offs Matrix",
            "## 21. Major Architectural Decisions (ADR Matrix)",
            "## 22. Resolved Cross-Agent Conflicts (Audit trail of arbitrations)",
            "## 23. Technical Risks & Failure Modes",
            "## 24. Known System Limitations",
            "## 25. Implementation Sequencing & Dependency Roadmap",
            "## 26. Acceptance Criteria (Testable validation assertions)",
            "## 27. Definition of Done (DoD Checklist)",
        ]

        for section_title in expected_sections:
            assert section_title in blueprint, f"Missing section: '{section_title}'"

    def test_build_traceability_matrix(self):
        state = _make_sample_project_state()
        architect = FinalArchitect()
        matrix = architect.build_traceability_matrix(state)

        assert "FR-001" in matrix
        assert "NFR-001" in matrix
        assert "AI-001" in matrix
        assert "SEC-001" in matrix
        assert len(matrix["FR-001"]) == 5
