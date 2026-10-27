"""
ProjectForge AI — Schema Validation Tests.

Tests every Pydantic model with valid mock data AND invalid boundary data to
ensure ``ValidationError`` is raised when constraints are violated.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AIArchitectureSpecification,
    Conflict,
    ConfidenceScore,
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


# ──────────────────────────────────────────────────────────────────────────────
# Reusable fixtures / helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_confidence(**overrides) -> dict:
    """Return a valid ConfidenceScore dict, with optional overrides."""
    base = {
        "score": 0.85,
        "fact_references": ["RFC-7231", "OWASP Top 10"],
        "unverified_assumptions": ["Assumes single-region deployment"],
        "risk_penalty": 0.1,
        "justification": "Based on industry benchmarks and prior experience.",
    }
    base.update(overrides)
    return base


def _make_tech_decision(**overrides) -> dict:
    """Return a valid TechDecision dict, with optional overrides."""
    base = {
        "category": "Backend Framework",
        "selected": "FastAPI",
        "version": "0.110.0",
        "why": "Best async Python framework for AI microservices.",
        "alternatives_rejected": {"Django": "Too heavyweight", "Flask": "No async native"},
        "tradeoffs": ["Smaller ecosystem than Django"],
        "failure_conditions": ["Extreme CPU-bound workloads"],
        "confidence": _make_confidence(),
    }
    base.update(overrides)
    return base


def _make_security_threat(**overrides) -> dict:
    """Return a valid SecurityThreat dict."""
    base = {
        "threat_id": "T-001",
        "stride_category": "Spoofing",
        "threat_description": "JWT token replay attack.",
        "severity": SeverityLevel.HIGH,
        "impact": "Unauthorised access to project data.",
        "likelihood": SeverityLevel.MEDIUM,
        "mitigation_strategy": "Short-lived tokens + refresh rotation.",
        "priority": 2,
    }
    base.update(overrides)
    return base


def _make_test_case(**overrides) -> dict:
    """Return a valid TestCase dict."""
    base = {
        "test_id": "TC-001",
        "target_component": "AuthService",
        "category": "unit",
        "scenario": "Login with valid credentials returns JWT.",
        "expected_outcome": "200 OK with access_token in body.",
        "traceable_requirement_id": "FR-AUTH-01",
    }
    base.update(overrides)
    return base


def _make_view_state(**overrides) -> dict:
    base = {
        "view_name": "Dashboard",
        "loading_state": "Skeleton cards",
        "empty_state": "Illustration with CTA",
        "error_state": "Toast notification",
        "success_state": "Populated cards",
    }
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────────
# 1. ConfidenceScore
# ──────────────────────────────────────────────────────────────────────────────


class TestConfidenceScore:
    def test_valid(self):
        cs = ConfidenceScore(**_make_confidence())
        assert cs.score == 0.85
        assert cs.risk_penalty == 0.1

    def test_score_too_high(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(**_make_confidence(score=1.5))

    def test_score_negative(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(**_make_confidence(score=-0.1))

    def test_risk_penalty_too_high(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(**_make_confidence(risk_penalty=0.5))

    def test_risk_penalty_negative(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(**_make_confidence(risk_penalty=-0.01))

    def test_boundary_score_zero(self):
        cs = ConfidenceScore(**_make_confidence(score=0.0))
        assert cs.score == 0.0

    def test_boundary_score_one(self):
        cs = ConfidenceScore(**_make_confidence(score=1.0))
        assert cs.score == 1.0

    def test_boundary_risk_penalty_zero(self):
        cs = ConfidenceScore(**_make_confidence(risk_penalty=0.0))
        assert cs.risk_penalty == 0.0

    def test_boundary_risk_penalty_max(self):
        cs = ConfidenceScore(**_make_confidence(risk_penalty=0.4))
        assert cs.risk_penalty == 0.4


# ──────────────────────────────────────────────────────────────────────────────
# 2. TechDecision
# ──────────────────────────────────────────────────────────────────────────────


class TestTechDecision:
    def test_valid(self):
        td = TechDecision(**_make_tech_decision())
        assert td.selected == "FastAPI"
        assert td.confidence.score == 0.85

    def test_optional_version_none(self):
        td = TechDecision(**_make_tech_decision(version=None))
        assert td.version is None

    def test_nested_confidence_invalid(self):
        """ConfidenceScore constraint should propagate through nesting."""
        with pytest.raises(ValidationError):
            TechDecision(**_make_tech_decision(confidence=_make_confidence(score=2.0)))


# ──────────────────────────────────────────────────────────────────────────────
# 3. ProductSpecification
# ──────────────────────────────────────────────────────────────────────────────


class TestProductSpecification:
    _valid = {
        "problem_statement": "Automate code-review triage.",
        "target_users": ["Engineering leads", "DevOps engineers"],
        "user_personas": [
            {"name": "Alice", "role": "Tech Lead", "pain_point": "PR overload"}
        ],
        "core_value_proposition": "Reduce PR review latency by 60%.",
        "functional_requirements": ["GitHub integration", "Slack notifications"],
        "mvp_features": ["PR analysis", "Auto-label", "Dashboard"],
        "future_scope": ["Multi-repo support"],
        "non_goals": ["Code generation"],
        "success_metrics": [{"metric": "Review latency", "target": "<2h"}],
        "product_risks": ["Adoption friction"],
    }

    def test_valid(self):
        ps = ProductSpecification(**self._valid)
        assert len(ps.mvp_features) == 3

    def test_mvp_features_exceeds_max_length(self):
        """max_length=5 means more than 5 items should fail."""
        oversize = {**self._valid, "mvp_features": [f"F{i}" for i in range(6)]}
        with pytest.raises(ValidationError):
            ProductSpecification(**oversize)

    def test_mvp_features_at_max_boundary(self):
        """Exactly 5 items should pass."""
        boundary = {**self._valid, "mvp_features": [f"F{i}" for i in range(5)]}
        ps = ProductSpecification(**boundary)
        assert len(ps.mvp_features) == 5

    def test_non_goals_empty_fails(self):
        """min_length=1 means empty list should fail."""
        invalid = {**self._valid, "non_goals": []}
        with pytest.raises(ValidationError):
            ProductSpecification(**invalid)

    def test_non_goals_single_item(self):
        """Exactly one non-goal should pass."""
        ps = ProductSpecification(**{**self._valid, "non_goals": ["Not doing X"]})
        assert len(ps.non_goals) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 4. AIArchitectureSpecification
# ──────────────────────────────────────────────────────────────────────────────


class TestAIArchitectureSpecification:
    def test_minimal_valid(self):
        spec = AIArchitectureSpecification(
            ai_required=False,
            necessity_justification="No ML needed.",
            problem_type=ProblemType.NONE,
        )
        assert spec.candidate_models == []
        assert spec.recommended_model is None

    def test_full_valid(self):
        spec = AIArchitectureSpecification(
            ai_required=True,
            necessity_justification="NLP classification needed.",
            problem_type=ProblemType.NLP_LLM,
            problem_formulation="Binary sentiment classification.",
            candidate_models=[TechDecision(**_make_tech_decision(category="Model"))],
            recommended_model=TechDecision(**_make_tech_decision(category="Model")),
            dataset_requirements={"size": "10k labelled examples"},
            training_vs_api_strategy="Fine-tune on proprietary data.",
            inference_latency_sla_ms=200,
            evaluation_metrics=["F1", "Precision", "Recall"],
            baseline_heuristic="Keyword regex classifier.",
            compute_and_cost_estimation={"monthly": "$500"},
            hallucination_and_drift_mitigation=["Output guardrails"],
        )
        assert spec.ai_required is True
        assert spec.inference_latency_sla_ms == 200


# ──────────────────────────────────────────────────────────────────────────────
# 5. EngineeringSpecification
# ──────────────────────────────────────────────────────────────────────────────


class TestEngineeringSpecification:
    def test_valid(self):
        spec = EngineeringSpecification(
            system_architecture_pattern="Modular monolith",
            frontend_architecture=TechDecision(**_make_tech_decision(category="Frontend")),
            backend_architecture=TechDecision(**_make_tech_decision(category="Backend")),
            database_primary=TechDecision(**_make_tech_decision(category="Database")),
            api_protocol=TechDecision(**_make_tech_decision(category="API")),
            storage_strategy=TechDecision(**_make_tech_decision(category="Storage")),
            observability_stack={"logging": "Loki", "metrics": "Prometheus"},
            mermaid_diagram="graph TD; A-->B;",
            scalability_limits_and_bottlenecks=["Single-region write bottleneck"],
        )
        assert spec.database_cache is None
        assert spec.async_processing is None


# ──────────────────────────────────────────────────────────────────────────────
# 6. ViewStateSpecification & UXSpecification
# ──────────────────────────────────────────────────────────────────────────────


class TestViewStateSpecification:
    def test_valid(self):
        vs = ViewStateSpecification(**_make_view_state())
        assert vs.view_name == "Dashboard"


class TestUXSpecification:
    def test_valid(self):
        spec = UXSpecification(
            primary_user_journey=["Login", "Create project", "View blueprint"],
            information_architecture={"Dashboard": ["Projects", "Settings"]},
            view_states=[ViewStateSpecification(**_make_view_state())],
            accessibility_standards=["WCAG 2.1 AA"],
            responsive_breakpoints={"mobile": "640px", "desktop": "1024px"},
        )
        assert len(spec.view_states) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 7. SecurityThreat & SecurityReport
# ──────────────────────────────────────────────────────────────────────────────


class TestSecurityThreat:
    def test_valid(self):
        st = SecurityThreat(**_make_security_threat())
        assert st.priority == 2

    def test_priority_too_low(self):
        with pytest.raises(ValidationError):
            SecurityThreat(**_make_security_threat(priority=0))

    def test_priority_too_high(self):
        with pytest.raises(ValidationError):
            SecurityThreat(**_make_security_threat(priority=6))

    def test_priority_boundary_min(self):
        st = SecurityThreat(**_make_security_threat(priority=1))
        assert st.priority == 1

    def test_priority_boundary_max(self):
        st = SecurityThreat(**_make_security_threat(priority=5))
        assert st.priority == 5

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            SecurityThreat(**_make_security_threat(severity="ULTRA"))


class TestSecurityReport:
    def test_valid(self):
        report = SecurityReport(
            authentication_mechanism=TechDecision(**_make_tech_decision(category="Auth")),
            authorization_model="RBAC",
            data_protection_at_rest="AES-256",
            data_protection_in_transit="TLS 1.3",
            input_validation_rules=["Sanitise HTML", "Max length 10k chars"],
            threat_catalog=[SecurityThreat(**_make_security_threat())],
        )
        assert report.ai_threat_mitigations == []


# ──────────────────────────────────────────────────────────────────────────────
# 8. TestCase & QASpecification
# ──────────────────────────────────────────────────────────────────────────────


class TestTestCase:
    def test_valid(self):
        tc = TestCase(**_make_test_case())
        assert tc.test_id == "TC-001"


class TestQASpecification:
    def test_valid(self):
        qa = QASpecification(
            test_pyramid_distribution={"unit": "70%", "integration": "20%", "e2e": "10%"},
            frameworks_and_tooling=[TechDecision(**_make_tech_decision(category="Testing"))],
            critical_test_cases=[TestCase(**_make_test_case())],
            performance_load_thresholds={"p99_latency": "500ms", "rps": "1000"},
        )
        assert qa.ai_model_validation_protocol is None


# ──────────────────────────────────────────────────────────────────────────────
# 9. Conflict
# ──────────────────────────────────────────────────────────────────────────────


class TestConflict:
    _valid = {
        "conflict_id": "C-001",
        "issue": "Database choice conflict.",
        "participating_agents": ["EngineeringAgent", "SecurityAgent"],
        "conflicting_recommendations": {
            "EngineeringAgent": "Use MongoDB",
            "SecurityAgent": "Use PostgreSQL",
        },
        "evaluation_criteria_scores": {
            "EngineeringAgent": {"performance": 0.9, "security": 0.5},
            "SecurityAgent": {"performance": 0.6, "security": 0.95},
        },
        "arbitrated_resolution": "Use PostgreSQL with JSON columns.",
        "technical_justification": "Security trumps marginal perf difference.",
        "compromise_penalties": ["Slightly higher write latency"],
        "confidence": 0.8,
    }

    def test_valid(self):
        c = Conflict(**self._valid)
        assert c.confidence == 0.8

    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            Conflict(**{**self._valid, "confidence": 1.5})

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            Conflict(**{**self._valid, "confidence": -0.1})


# ──────────────────────────────────────────────────────────────────────────────
# 10. ProjectState (top-level aggregate)
# ──────────────────────────────────────────────────────────────────────────────


class TestProjectState:
    _minimal = {
        "project_id": "proj-001",
        "status": ProjectStatus.INTAKE,
        "raw_idea": "Build an AI-powered code review tool.",
        "intake_qa": {"q1": "What language?", "a1": "Python"},
    }

    def test_minimal_valid(self):
        ps = ProjectState(**self._minimal)
        assert ps.revision == 1
        assert ps.detected_conflicts == []
        assert ps.audit_traceability_matrix == {}

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            ProjectState(**{**self._minimal, "status": "INVALID_STATUS"})

    def test_with_product_spec(self):
        ps = ProjectState(
            **{
                **self._minimal,
                "product_spec": {
                    "problem_statement": "Automate triage.",
                    "target_users": ["Devs"],
                    "user_personas": [{"name": "Bob", "role": "Dev"}],
                    "core_value_proposition": "Save time.",
                    "functional_requirements": ["Integration"],
                    "mvp_features": ["Feature A"],
                    "future_scope": ["Feature B"],
                    "non_goals": ["Not this"],
                    "success_metrics": [{"metric": "Speed"}],
                    "product_risks": ["Adoption"],
                },
            }
        )
        assert ps.product_spec is not None
        assert ps.product_spec.problem_statement == "Automate triage."

    def test_nested_validation_propagates(self):
        """ProductSpec with empty non_goals should fail even inside ProjectState."""
        with pytest.raises(ValidationError):
            ProjectState(
                **{
                    **self._minimal,
                    "product_spec": {
                        "problem_statement": "X",
                        "target_users": ["U"],
                        "user_personas": [{"name": "A"}],
                        "core_value_proposition": "V",
                        "functional_requirements": ["R"],
                        "mvp_features": ["F"],
                        "future_scope": ["S"],
                        "non_goals": [],  # <-- should fail min_length=1
                        "success_metrics": [{"m": "v"}],
                        "product_risks": ["P"],
                    },
                }
            )


# ──────────────────────────────────────────────────────────────────────────────
# 11. Enum coverage
# ──────────────────────────────────────────────────────────────────────────────


class TestEnums:
    def test_severity_values(self):
        assert set(SeverityLevel) == {
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        }

    def test_problem_type_values(self):
        assert ProblemType.NONE.value == "NONE"
        assert ProblemType.NLP_LLM.value == "NLP_LLM"

    def test_project_status_values(self):
        assert ProjectStatus.INTAKE.value == "INTAKE"
        assert ProjectStatus.COMPLETED.value == "COMPLETED"
        assert {"FAILED", "BLOCKED", "CANCELLED"}.issubset({s.value for s in ProjectStatus})
