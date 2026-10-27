"""
ProjectForge AI — Agent Unit Tests.

Tests all 7 specialized agents with mocked LLM clients, validating:
  - Successful first-pass structured responses
  - Malformed JSON recovery on retry
  - Custom lint rule enforcement triggering re-prompts
  - Output adherence to respective Pydantic schemas
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from app.agents.intake_agent import IntakeAgent
from app.agents.product_agent import ProductAgent
from app.agents.aiml_agent import AIMLAgent
from app.agents.engineering_agent import EngineeringAgent
from app.agents.ux_agent import UXAgent
from app.agents.security_agent import SecurityAgent
from app.agents.qa_agent import QAAgent

from app.models.schemas import (
    AIArchitectureSpecification,
    EngineeringSpecification,
    IntakeClarifications,
    ProductSpecification,
    QASpecification,
    SecurityReport,
    UXSpecification,
)


# ══════════════════════════════════════════════════════════════════════════════
# Shared test fixtures
# ══════════════════════════════════════════════════════════════════════════════


def _make_confidence(**overrides) -> dict:
    base = {
        "score": 0.85,
        "fact_references": ["RFC-7231", "OWASP Top 10"],
        "unverified_assumptions": ["Assumes single-region"],
        "risk_penalty": 0.1,
        "justification": "Industry benchmarks.",
    }
    base.update(overrides)
    return base


def _make_tech_decision(**overrides) -> dict:
    base = {
        "category": "Framework",
        "selected": "FastAPI",
        "version": "0.110.0",
        "why": "Best async Python framework.",
        "alternatives_rejected": {
            "Django": "Too heavyweight for microservices",
            "Flask": "No native async support",
        },
        "tradeoffs": ["Smaller ecosystem than Django"],
        "failure_conditions": ["CPU-bound workloads"],
        "confidence": _make_confidence(),
    }
    base.update(overrides)
    return base


def _make_project_state(**overrides) -> Dict[str, Any]:
    """Build a representative project state dict for agent testing."""
    base: Dict[str, Any] = {
        "project_id": "proj-test-001",
        "revision": 1,
        "status": "INTAKE",
        "raw_idea": "Build an AI-powered code review tool for GitHub PRs",
        "intake_qa": {
            "Q1": "Automate PR triage and review prioritisation",
            "Q2": "Engineering leads at mid-size SaaS companies",
            "Q3": "Submit PR → Auto-analyse → Label → Notify reviewer",
            "Q4": "PR analysis, auto-labelling, reviewer dashboard",
            "Q5": "GitHub webhooks, PR diffs (JSON/text, ~1k PRs/day)",
            "Q6": "Review labels, priority scores, Slack notifications",
            "Q7": "NLP classification for PR complexity scoring",
            "Q8": "Must run on AWS, budget ≤ $2k/month",
            "Q9": "99.5% uptime, ~500 concurrent users",
            "Q10": "Reduce PR review latency by 40% within 3 months",
        },
        "product_spec": {
            "problem_statement": "Slow PR reviews blocking deployments",
            "functional_requirements": ["GitHub integration", "Slack alerts"],
            "non_goals": ["Code generation"],
            "target_users": ["Engineering leads"],
            "user_personas": [{"name": "Alice", "role": "Lead"}],
            "core_value_proposition": "Cut review latency by 40%",
            "mvp_features": ["PR analysis", "Dashboard"],
            "future_scope": ["Multi-repo"],
            "success_metrics": [{"metric": "Review latency", "target": "<2h"}],
            "product_risks": ["Adoption friction"],
        },
        "ai_spec": {
            "ai_required": True,
            "problem_type": "NLP_LLM",
            "necessity_justification": "NLP needed for PR classification",
        },
        "engineering_spec": {
            "system_architecture_pattern": "Microservices",
            "frontend_architecture": _make_tech_decision(
                category="Frontend", selected="React"
            ),
            "backend_architecture": _make_tech_decision(
                category="Backend", selected="FastAPI"
            ),
        },
        "security_report": {"authorization_model": "RBAC"},
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# 1. INTAKE AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_intake_json() -> str:
    return json.dumps({
        "questions": [
            {
                "question_id": "Q5",
                "question_text": "What data formats will PRs contain?",
                "why_asked": "Engineering agent needs input data specs.",
                "expected_answer_type": "free_text",
            },
            {
                "question_id": "Q9",
                "question_text": "What is your uptime SLA requirement?",
                "why_asked": "Engineering agent needs availability targets.",
                "expected_answer_type": "single_choice",
            },
        ]
    })


class TestIntakeAgent:
    @pytest.mark.asyncio
    async def test_successful_clarifications(self):
        mock_llm = MagicMock(return_value=_make_valid_intake_json())
        agent = IntakeAgent(llm_client=mock_llm)

        result = await agent.generate_adaptive_clarifications(
            idea="Build a code review tool",
            partial_answers={"Q1": "Automate PR triage"},
        )

        assert result.success is True
        assert isinstance(result.output, IntakeClarifications)
        assert len(result.output.questions) == 2
        assert result.output.questions[0].question_id == "Q5"

    @pytest.mark.asyncio
    async def test_invalid_question_id_triggers_retry(self):
        """question_id outside Q1–Q10 should fail lint."""
        bad_json = json.dumps({
            "questions": [{
                "question_id": "Q99",
                "question_text": "Invalid?",
                "why_asked": "test",
                "expected_answer_type": "free_text",
            }]
        })
        valid_json = _make_valid_intake_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = IntakeAgent(llm_client=mock_llm)
        result = await agent.generate_adaptive_clarifications(
            idea="Build X", partial_answers={},
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_malformed_json_recovers(self):
        bad_json = '{"questions": "not a list"}'
        valid_json = _make_valid_intake_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = IntakeAgent(llm_client=mock_llm)
        result = await agent.generate_adaptive_clarifications(
            idea="Build X", partial_answers={},
        )

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 2. PRODUCT AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_product_json() -> str:
    return json.dumps({
        "problem_statement": "PR reviews block deployment velocity.",
        "target_users": ["Engineering leads", "DevOps engineers"],
        "user_personas": [
            {"name": "Alice", "role": "Tech Lead",
             "pain_point": "PR overload", "goal": "Reduce review time"}
        ],
        "core_value_proposition": "Reduce PR review latency by 40%.",
        "functional_requirements": [
            "GitHub webhook integration",
            "Automated PR complexity scoring",
            "Slack notification service",
        ],
        "mvp_features": ["PR analysis", "Auto-label", "Dashboard"],
        "future_scope": ["Multi-repo support", "GitLab integration"],
        "non_goals": ["Automated code generation", "CI/CD pipeline management"],
        "success_metrics": [
            {"metric": "Review latency", "target": "Reduce by 40% in 3 months"},
            {"metric": "Reviewer satisfaction", "target": "NPS > 50"},
        ],
        "product_risks": ["Low adoption rate", "Inaccurate PR scoring"],
    })


class TestProductAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_llm = MagicMock(return_value=_make_valid_product_json())
        agent = ProductAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, ProductSpecification)
        assert len(result.output.mvp_features) <= 5
        assert len(result.output.non_goals) >= 1

    @pytest.mark.asyncio
    async def test_non_quantifiable_metrics_triggers_retry(self):
        """Metrics without numbers should fail the custom lint rule."""
        bad_json = json.dumps({
            "problem_statement": "Slow reviews.",
            "target_users": ["Engineers"],
            "user_personas": [{"name": "A", "role": "Dev"}],
            "core_value_proposition": "Save time.",
            "functional_requirements": ["Integration"],
            "mvp_features": ["Feature A"],
            "future_scope": ["Feature B"],
            "non_goals": ["Not this"],
            "success_metrics": [
                {"metric": "Efficiency", "target": "improve significantly"},
            ],
            "product_risks": ["Risk A"],
        })
        valid_json = _make_valid_product_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = ProductAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_malformed_json_recovers(self):
        bad_json = '{"problem_statement": 42}'
        valid_json = _make_valid_product_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = ProductAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 3. AI/ML AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_aiml_no_ai_json() -> str:
    """Valid AIArchitectureSpecification with ai_required=false."""
    return json.dumps({
        "ai_required": False,
        "necessity_justification": "Simple keyword matching suffices.",
        "problem_type": "NONE",
    })


def _make_valid_aiml_with_ai_json() -> str:
    """Valid AIArchitectureSpecification with ai_required=true."""
    return json.dumps({
        "ai_required": True,
        "necessity_justification": "NLP classification needed for PR complexity.",
        "problem_type": "NLP_LLM",
        "problem_formulation": "Multi-class text classification on PR diffs.",
        "candidate_models": [
            _make_tech_decision(
                category="LLM", selected="GPT-4o-mini",
                why="Cost-effective for classification",
            ),
            _make_tech_decision(
                category="LLM", selected="Claude Haiku",
                why="Fast inference, lower cost",
            ),
        ],
        "recommended_model": _make_tech_decision(
            category="LLM", selected="GPT-4o-mini",
            why="Best balance of cost and accuracy",
        ),
        "dataset_requirements": {"size": "10k labelled PRs"},
        "training_vs_api_strategy": "API-based with fine-tuning later.",
        "inference_latency_sla_ms": 200,
        "evaluation_metrics": ["F1-score", "Precision", "Recall"],
        "baseline_heuristic": "Keyword regex classifier (F1=0.45).",
        "compute_and_cost_estimation": {"monthly": "$500"},
        "hallucination_and_drift_mitigation": [
            "Output guardrails with schema validation",
        ],
    })


class TestAIMLAgent:
    @pytest.mark.asyncio
    async def test_no_ai_required(self):
        mock_llm = MagicMock(return_value=_make_valid_aiml_no_ai_json())
        agent = AIMLAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, AIArchitectureSpecification)
        assert result.output.ai_required is False
        assert result.output.problem_type.value == "NONE"

    @pytest.mark.asyncio
    async def test_ai_required_full_spec(self):
        mock_llm = MagicMock(return_value=_make_valid_aiml_with_ai_json())
        agent = AIMLAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.output.ai_required is True
        assert len(result.output.candidate_models) >= 2
        assert result.output.recommended_model is not None

    @pytest.mark.asyncio
    async def test_zero_ai_inconsistency_triggers_retry(self):
        """ai_required=false with non-NONE problem_type should fail lint."""
        bad_json = json.dumps({
            "ai_required": False,
            "necessity_justification": "No AI needed.",
            "problem_type": "NLP_LLM",  # inconsistent!
        })
        valid_json = _make_valid_aiml_no_ai_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = AIMLAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 4. ENGINEERING AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_engineering_json() -> str:
    return json.dumps({
        "system_architecture_pattern": "Modular Monolith",
        "frontend_architecture": _make_tech_decision(
            category="Frontend", selected="React", version="18.3",
        ),
        "backend_architecture": _make_tech_decision(
            category="Backend", selected="FastAPI", version="0.110.0",
        ),
        "database_primary": _make_tech_decision(
            category="Database", selected="PostgreSQL", version="16",
        ),
        "api_protocol": _make_tech_decision(
            category="API", selected="REST/OpenAPI",
        ),
        "storage_strategy": _make_tech_decision(
            category="Storage", selected="S3",
        ),
        "observability_stack": {
            "logging": "Loki",
            "metrics": "Prometheus",
            "tracing": "Jaeger",
        },
        "mermaid_diagram": (
            "graph TD\n"
            "    Client-->|HTTPS|API_Gateway\n"
            "    API_Gateway-->Backend\n"
            "    Backend-->PostgreSQL\n"
            "    Backend-->S3"
        ),
        "scalability_limits_and_bottlenecks": [
            "Single-node PostgreSQL write limit at ~10k TPS",
            "WebSocket connection limit per instance: ~65k",
        ],
    })


class TestEngineeringAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_llm = MagicMock(return_value=_make_valid_engineering_json())
        agent = EngineeringAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, EngineeringSpecification)
        assert result.output.mermaid_diagram.startswith("graph")
        assert len(result.output.scalability_limits_and_bottlenecks) >= 2

    @pytest.mark.asyncio
    async def test_invalid_mermaid_triggers_retry(self):
        """Mermaid diagram not starting with valid directive fails lint."""
        bad_spec = json.loads(_make_valid_engineering_json())
        bad_spec["mermaid_diagram"] = "NOT A VALID DIAGRAM"
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_engineering_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = EngineeringAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_insufficient_bottlenecks_triggers_retry(self):
        """Less than 2 bottlenecks should fail lint."""
        bad_spec = json.loads(_make_valid_engineering_json())
        bad_spec["scalability_limits_and_bottlenecks"] = ["Only one"]
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_engineering_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = EngineeringAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 5. UX AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_ux_json() -> str:
    return json.dumps({
        "primary_user_journey": [
            "Sign up / Log in",
            "Connect GitHub repository",
            "View PR analysis dashboard",
            "Configure notification preferences",
        ],
        "information_architecture": {
            "Dashboard": ["PR List", "Analytics", "Settings"],
            "PR Detail": ["Diff View", "Complexity Score", "Review History"],
        },
        "view_states": [
            {
                "view_name": "Dashboard",
                "loading_state": "Skeleton card grid with pulse animation",
                "empty_state": "Illustration with 'Connect your first repo' CTA",
                "error_state": "Toast notification with retry button",
                "success_state": "Populated card grid with PR summaries",
            },
            {
                "view_name": "PR Detail",
                "loading_state": "Diff skeleton with shimmer effect",
                "empty_state": "No changes detected message",
                "error_state": "Error banner with support link",
                "success_state": "Full diff view with inline annotations",
            },
        ],
        "accessibility_standards": [
            "WCAG 2.1 AA colour contrast ratio ≥ 4.5:1",
            "All interactive elements keyboard-navigable",
            "Screen reader compatible with ARIA landmarks",
        ],
        "responsive_breakpoints": {
            "mobile": "0–639px",
            "tablet": "640–1023px",
            "desktop": "1024px+",
        },
    })


class TestUXAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_llm = MagicMock(return_value=_make_valid_ux_json())
        agent = UXAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, UXSpecification)
        assert len(result.output.primary_user_journey) >= 3
        assert len(result.output.view_states) >= 2

    @pytest.mark.asyncio
    async def test_missing_breakpoint_triggers_retry(self):
        """Missing 'tablet' breakpoint should fail lint."""
        bad_spec = json.loads(_make_valid_ux_json())
        bad_spec["responsive_breakpoints"] = {
            "mobile": "0–639px",
            "desktop": "1024px+",
            # missing 'tablet'
        }
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_ux_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = UXAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_short_user_journey_triggers_retry(self):
        """Fewer than 3 journey steps should fail lint."""
        bad_spec = json.loads(_make_valid_ux_json())
        bad_spec["primary_user_journey"] = ["Login", "Dashboard"]
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_ux_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = UXAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 6. SECURITY AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_security_json() -> str:
    return json.dumps({
        "authentication_mechanism": _make_tech_decision(
            category="Authentication", selected="JWT + OAuth 2.0",
        ),
        "authorization_model": "RBAC with role hierarchy (Admin > Lead > Dev)",
        "data_protection_at_rest": "AES-256 encryption for PII columns",
        "data_protection_in_transit": "TLS 1.3 for all endpoints",
        "input_validation_rules": [
            "Sanitise all HTML input with DOMPurify",
            "Max request body size: 10MB",
            "Rate limit: 100 req/min per API key",
        ],
        "ai_threat_mitigations": [
            "Prompt injection guard via input sanitisation",
            "Model inversion prevention via output truncation",
            "Data poisoning detection via training data checksums",
        ],
        "threat_catalog": [
            {
                "threat_id": "T-001",
                "stride_category": "Spoofing",
                "threat_description": "JWT token replay after expiry.",
                "severity": "HIGH",
                "impact": "Unauthorised access to project data.",
                "likelihood": "MEDIUM",
                "mitigation_strategy": "Short-lived tokens (15min) + refresh rotation.",
                "priority": 2,
            },
            {
                "threat_id": "T-002",
                "stride_category": "Tampering",
                "threat_description": "PR diff payload manipulation.",
                "severity": "HIGH",
                "impact": "Incorrect complexity scoring.",
                "likelihood": "LOW",
                "mitigation_strategy": "Webhook signature verification (HMAC-SHA256).",
                "priority": 3,
            },
            {
                "threat_id": "T-003",
                "stride_category": "Information Disclosure",
                "threat_description": "Source code leakage through error messages.",
                "severity": "MEDIUM",
                "impact": "Exposure of internal architecture.",
                "likelihood": "MEDIUM",
                "mitigation_strategy": "Structured error responses without stack traces.",
                "priority": 2,
            },
        ],
    })


class TestSecurityAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_llm = MagicMock(return_value=_make_valid_security_json())
        agent = SecurityAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, SecurityReport)
        assert len(result.output.threat_catalog) >= 3
        assert result.output.authorization_model != ""

    @pytest.mark.asyncio
    async def test_invalid_stride_category_triggers_retry(self):
        """Invalid STRIDE category should fail lint."""
        bad_spec = json.loads(_make_valid_security_json())
        bad_spec["threat_catalog"][0]["stride_category"] = "InvalidCategory"
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_security_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = SecurityAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_too_few_threats_triggers_retry(self):
        """Fewer than 3 threats should fail lint."""
        bad_spec = json.loads(_make_valid_security_json())
        bad_spec["threat_catalog"] = bad_spec["threat_catalog"][:2]
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_security_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = SecurityAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2


# ══════════════════════════════════════════════════════════════════════════════
# 7. QA AGENT
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_qa_json() -> str:
    return json.dumps({
        "test_pyramid_distribution": {
            "unit": "70%",
            "integration": "20%",
            "e2e": "10%",
        },
        "frameworks_and_tooling": [
            _make_tech_decision(
                category="Unit Testing", selected="pytest", version="8.0",
            ),
        ],
        "critical_test_cases": [
            {
                "test_id": "TC-001",
                "target_component": "PRAnalysisService",
                "category": "unit",
                "scenario": "Submit valid PR diff and verify complexity score.",
                "expected_outcome": "Returns complexity_score between 0.0 and 1.0.",
                "traceable_requirement_id": "FR-ANALYSIS-01",
            },
            {
                "test_id": "TC-002",
                "target_component": "AuthService",
                "category": "integration",
                "scenario": "Login with valid GitHub OAuth credentials.",
                "expected_outcome": "200 OK with JWT access_token in response body.",
                "traceable_requirement_id": "FR-AUTH-01",
            },
            {
                "test_id": "TC-003",
                "target_component": "NotificationService",
                "category": "integration",
                "scenario": "Trigger Slack notification on PR label assignment.",
                "expected_outcome": "Slack API called with correct channel and message.",
                "traceable_requirement_id": "FR-NOTIFY-01",
            },
        ],
        "performance_load_thresholds": {
            "p99_latency": "500ms",
            "rps": "1000",
            "concurrent_users": "500",
        },
    })


class TestQAAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        mock_llm = MagicMock(return_value=_make_valid_qa_json())
        agent = QAAgent(llm_client=mock_llm)

        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert isinstance(result.output, QASpecification)
        assert len(result.output.critical_test_cases) >= 3
        pyramid = result.output.test_pyramid_distribution
        assert "unit" in pyramid
        assert "integration" in pyramid
        assert "e2e" in pyramid

    @pytest.mark.asyncio
    async def test_missing_pyramid_key_triggers_retry(self):
        """Missing 'e2e' key should fail lint."""
        bad_spec = json.loads(_make_valid_qa_json())
        bad_spec["test_pyramid_distribution"] = {"unit": "80%", "integration": "20%"}
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_qa_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = QAAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_too_few_test_cases_triggers_retry(self):
        """Fewer than 3 test cases should fail lint."""
        bad_spec = json.loads(_make_valid_qa_json())
        bad_spec["critical_test_cases"] = bad_spec["critical_test_cases"][:2]
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_qa_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = QAAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_missing_perf_threshold_triggers_retry(self):
        """Missing 'rps' threshold should fail lint."""
        bad_spec = json.loads(_make_valid_qa_json())
        bad_spec["performance_load_thresholds"] = {"p99_latency": "500ms"}
        bad_json = json.dumps(bad_spec)
        valid_json = _make_valid_qa_json()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        agent = QAAgent(llm_client=mock_llm)
        result = await agent.analyze(_make_project_state())

        assert result.success is True
        assert result.attempts == 2
