"""
ProjectForge AI — Harness Unit Tests.

Covers:
  - calibration.py     → formula correctness, edge cases, clamping, errors
  - context_filter.py  → ContextFilter per-agent methods, field stripping,
                          deep-copy isolation, Q-key extraction
  - base_harness.py    → AgentExecutionHarness: successful first-pass,
                          malformed-JSON recovery on retry, lint-rule
                          re-prompting, LLM exception handling, confidence
                          calibration walk, built-in lint rules
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from app.harness.calibration import compute_calibrated_confidence
from app.harness.context_filter import ContextFilter
from app.harness.base_harness import (
    AgentExecutionHarness,
    HarnessResult,
    calibrate_confidence_in_place,
    lint_tech_decision_alternatives,
    lint_non_empty_non_goals,
    build_diagnostic_retry_prompt,
    build_lint_retry_prompt,
)
from app.models.schemas import (
    ConfidenceScore,
    ProductSpecification,
    TechDecision,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CALIBRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestComputeCalibratedConfidence:
    """Tests for the calibration formula:
    C = (E / (E + A)) × (1 − P_risk), clamped [0.05, 0.98].
    """

    def test_basic_calculation(self):
        # E=8, A=2, P=0.1 → (8/10)*(0.9) = 0.72
        assert compute_calibrated_confidence(8, 2, 0.1) == pytest.approx(0.72)

    def test_all_facts_no_assumptions(self):
        # E=5, A=0, P=0.0 → (5/5)*(1.0) = 1.0 → clamped to 0.98
        assert compute_calibrated_confidence(5, 0, 0.0) == pytest.approx(0.98)

    def test_no_facts_all_assumptions(self):
        # E=0, A=5, P=0.0 → (0/5)*(1.0) = 0.0 → clamped to 0.05
        assert compute_calibrated_confidence(0, 5, 0.0) == pytest.approx(0.05)

    def test_zero_evidence_zero_assumptions(self):
        # Edge: no data at all → evidence_ratio=0 → clamp 0.05
        assert compute_calibrated_confidence(0, 0, 0.0) == pytest.approx(0.05)

    def test_max_risk_penalty(self):
        # E=10, A=0, P=0.4 → (1.0)*(0.6) = 0.6
        assert compute_calibrated_confidence(10, 0, 0.4) == pytest.approx(0.6)

    def test_ceiling_clamp(self):
        result = compute_calibrated_confidence(100, 0, 0.0)
        assert result == pytest.approx(0.98)

    def test_floor_clamp(self):
        result = compute_calibrated_confidence(0, 100, 0.0)
        assert result == pytest.approx(0.05)

    def test_risk_penalty_above_04_clamped_to_1(self):
        # risk_penalty=1.0 → (1 − 1.0)=0 → clamped to 0.05
        result = compute_calibrated_confidence(10, 0, 1.0)
        assert result == pytest.approx(0.05)

    def test_negative_risk_penalty_clamped_to_zero(self):
        result = compute_calibrated_confidence(5, 0, -0.5)
        assert result == pytest.approx(0.98)

    def test_negative_fact_count_raises(self):
        with pytest.raises(ValueError, match="fact_count"):
            compute_calibrated_confidence(-1, 0, 0.0)

    def test_negative_assumptions_count_raises(self):
        with pytest.raises(ValueError, match="unverified_assumptions_count"):
            compute_calibrated_confidence(0, -1, 0.0)

    def test_equal_facts_and_assumptions(self):
        # E=5, A=5, P=0.2 → (0.5)*(0.8) = 0.4
        assert compute_calibrated_confidence(5, 5, 0.2) == pytest.approx(0.4)

    def test_large_numbers(self):
        # E=1000, A=1, P=0.0 → ≈0.999 → clamped to 0.98
        assert compute_calibrated_confidence(1000, 1, 0.0) == pytest.approx(0.98)


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONTEXT FILTER TESTS
# ══════════════════════════════════════════════════════════════════════════════


def _make_full_state() -> Dict[str, Any]:
    """Build a full ProjectState dict with all intake Q-keys."""
    return {
        "project_id": "proj-001",
        "revision": 1,
        "status": "INTAKE",
        "raw_idea": "Build an AI code review tool",
        "intake_qa": {
            "Q1": "What is the product?",
            "Q2": "Who are the target users?",
            "Q3": "What platforms?",
            "Q4": "Core features?",
            "Q5": "Tech stack preferences?",
            "Q6": "Scale expectations?",
            "Q7": "Data sources?",
            "Q8": "Budget constraints?",
            "Q9": "Timeline?",
            "Q10": "Success metrics?",
        },
        "product_spec": {
            "problem_statement": "Slow code review",
            "functional_requirements": ["GitHub integration", "Slack alerts"],
            "non_goals": ["Code generation"],
        },
        "ai_spec": {
            "ai_required": True,
            "problem_type": "NLP_LLM",
        },
        "engineering_spec": {
            "system_architecture_pattern": "Microservices",
            "frontend_architecture": {"selected": "React", "category": "Frontend"},
            "backend_architecture": {"selected": "FastAPI", "category": "Backend"},
        },
        "ux_spec": {"primary_user_journey": ["Login", "Dashboard"]},
        "security_report": {"authorization_model": "RBAC"},
        "qa_spec": {"test_pyramid_distribution": {"unit": "70%"}},
        "detected_conflicts": [{"conflict_id": "C-001"}],
        "final_blueprint_markdown": "# Blueprint",
        "audit_traceability_matrix": {"FR-01": ["TC-001"]},
    }


class TestContextFilterProduct:
    """Tests for ContextFilter.for_product."""

    def test_returns_raw_idea(self):
        ctx = ContextFilter.for_product(_make_full_state())
        assert ctx["raw_idea"] == "Build an AI code review tool"

    def test_returns_correct_intake_keys(self):
        ctx = ContextFilter.for_product(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {"Q1", "Q2", "Q3", "Q4", "Q10"}

    def test_strips_engineering_spec(self):
        ctx = ContextFilter.for_product(_make_full_state())
        assert "engineering_spec" not in ctx

    def test_strips_ai_spec(self):
        ctx = ContextFilter.for_product(_make_full_state())
        assert "ai_spec" not in ctx

    def test_deep_copy_isolation(self):
        state = _make_full_state()
        ctx = ContextFilter.for_product(state)
        ctx["intake_qa"]["Q1"] = "MUTATED"
        assert state["intake_qa"]["Q1"] == "What is the product?"


class TestContextFilterAIML:
    """Tests for ContextFilter.for_aiml."""

    def test_returns_correct_intake_keys(self):
        ctx = ContextFilter.for_aiml(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {
            "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10"
        }

    def test_returns_functional_requirements(self):
        ctx = ContextFilter.for_aiml(_make_full_state())
        assert ctx["functional_requirements"] == [
            "GitHub integration", "Slack alerts"
        ]

    def test_strips_raw_idea(self):
        ctx = ContextFilter.for_aiml(_make_full_state())
        assert "raw_idea" not in ctx

    def test_strips_full_product_spec(self):
        ctx = ContextFilter.for_aiml(_make_full_state())
        assert "product_spec" not in ctx


class TestContextFilterEngineering:
    """Tests for ContextFilter.for_engineering."""

    def test_returns_correct_intake_keys(self):
        ctx = ContextFilter.for_engineering(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {"Q5", "Q6", "Q8", "Q9"}

    def test_includes_product_spec(self):
        ctx = ContextFilter.for_engineering(_make_full_state())
        assert ctx["product_spec"] is not None

    def test_includes_ai_spec(self):
        ctx = ContextFilter.for_engineering(_make_full_state())
        assert ctx["ai_spec"] is not None


class TestContextFilterUX:
    """Tests for ContextFilter.for_ux."""

    def test_returns_correct_intake_keys(self):
        ctx = ContextFilter.for_ux(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {"Q2", "Q3"}

    def test_includes_product_spec(self):
        ctx = ContextFilter.for_ux(_make_full_state())
        assert ctx["product_spec"] is not None

    def test_extracts_frontend_architecture_only(self):
        ctx = ContextFilter.for_ux(_make_full_state())
        assert ctx["frontend_architecture"]["selected"] == "React"
        assert "engineering_spec" not in ctx

    def test_strips_backend_architecture(self):
        ctx = ContextFilter.for_ux(_make_full_state())
        assert "backend_architecture" not in ctx


class TestContextFilterSecurity:
    """Tests for ContextFilter.for_security."""

    def test_returns_correct_intake_keys(self):
        ctx = ContextFilter.for_security(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {"Q5", "Q8", "Q9"}

    def test_includes_engineering_spec(self):
        ctx = ContextFilter.for_security(_make_full_state())
        assert ctx["engineering_spec"] is not None

    def test_includes_ai_spec(self):
        ctx = ContextFilter.for_security(_make_full_state())
        assert ctx["ai_spec"] is not None

    def test_strips_product_spec(self):
        ctx = ContextFilter.for_security(_make_full_state())
        assert "product_spec" not in ctx


class TestContextFilterQA:
    """Tests for ContextFilter.for_qa."""

    def test_includes_all_four_specs(self):
        ctx = ContextFilter.for_qa(_make_full_state())
        assert "product_spec" in ctx
        assert "engineering_spec" in ctx
        assert "security_report" in ctx
        assert "ai_spec" in ctx

    def test_strips_intake_qa(self):
        ctx = ContextFilter.for_qa(_make_full_state())
        assert "intake_qa" not in ctx

    def test_strips_raw_idea(self):
        ctx = ContextFilter.for_qa(_make_full_state())
        assert "raw_idea" not in ctx


class TestContextFilterConflictResolver:
    """Tests for ContextFilter.for_conflict_resolver."""

    def test_includes_all_specs(self):
        ctx = ContextFilter.for_conflict_resolver(_make_full_state())
        for key in [
            "product_spec", "ai_spec", "engineering_spec",
            "ux_spec", "security_report", "qa_spec",
        ]:
            assert key in ctx, f"Missing key: {key}"

    def test_includes_detected_conflicts(self):
        ctx = ContextFilter.for_conflict_resolver(_make_full_state())
        assert len(ctx["detected_conflicts"]) == 1

    def test_includes_user_constraints_q8_q9(self):
        ctx = ContextFilter.for_conflict_resolver(_make_full_state())
        assert set(ctx["intake_qa"].keys()) == {"Q8", "Q9"}

    def test_strips_raw_idea(self):
        ctx = ContextFilter.for_conflict_resolver(_make_full_state())
        assert "raw_idea" not in ctx


class TestContextFilterFinalArchitect:
    """Tests for ContextFilter.for_final_architect."""

    def test_returns_entire_state(self):
        state = _make_full_state()
        ctx = ContextFilter.for_final_architect(state)
        assert set(ctx.keys()) == set(state.keys())

    def test_deep_copy_isolation(self):
        state = _make_full_state()
        ctx = ContextFilter.for_final_architect(state)
        ctx["raw_idea"] = "MUTATED"
        assert state["raw_idea"] == "Build an AI code review tool"


# ══════════════════════════════════════════════════════════════════════════════
# 3. BUILT-IN LINT RULE TESTS
# ══════════════════════════════════════════════════════════════════════════════


def _make_confidence(**overrides) -> dict:
    base = {
        "score": 0.85,
        "fact_references": ["ref1", "ref2"],
        "unverified_assumptions": ["asm1"],
        "risk_penalty": 0.1,
        "justification": "Solid evidence.",
    }
    base.update(overrides)
    return base


def _make_tech_decision(**overrides) -> dict:
    base = {
        "category": "Backend Framework",
        "selected": "FastAPI",
        "version": "0.110.0",
        "why": "Best async framework.",
        "alternatives_rejected": {
            "Django": "Too heavy",
            "Flask": "No native async",
        },
        "tradeoffs": ["Smaller ecosystem"],
        "failure_conditions": ["CPU-bound loads"],
        "confidence": _make_confidence(),
    }
    base.update(overrides)
    return base


class TestLintTechDecisionAlternatives:
    def test_passes_with_2_alternatives(self):
        td = TechDecision(**_make_tech_decision())
        violations = lint_tech_decision_alternatives(td)
        assert violations == []

    def test_fails_with_1_alternative(self):
        td = TechDecision(**_make_tech_decision(
            alternatives_rejected={"Django": "Too heavy"}
        ))
        violations = lint_tech_decision_alternatives(td)
        assert len(violations) == 1
        assert "minimum is 2" in violations[0]

    def test_fails_with_0_alternatives(self):
        td = TechDecision(**_make_tech_decision(
            alternatives_rejected={}
        ))
        violations = lint_tech_decision_alternatives(td)
        assert len(violations) == 1


class TestLintNonEmptyNonGoals:
    def test_passes_with_non_goals(self):
        ps = ProductSpecification(
            problem_statement="X",
            target_users=["U"],
            user_personas=[{"name": "A"}],
            core_value_proposition="V",
            functional_requirements=["R"],
            mvp_features=["F"],
            future_scope=["S"],
            non_goals=["Not doing this"],
            success_metrics=[{"m": "v"}],
            product_risks=["P"],
        )
        violations = lint_non_empty_non_goals(ps)
        assert violations == []


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONFIDENCE CALIBRATION WALK TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestCalibrateConfidenceInPlace:
    def test_direct_confidence_score(self):
        cs = ConfidenceScore(
            score=0.99,
            fact_references=["ref1", "ref2"],
            unverified_assumptions=["asm1"],
            risk_penalty=0.1,
            justification="test",
        )
        calibrate_confidence_in_place(cs)
        # (2/3) * (0.9) ≈ 0.6
        assert cs.score == pytest.approx(0.6, abs=0.01)

    def test_nested_in_tech_decision(self):
        td = TechDecision(
            category="DB",
            selected="PostgreSQL",
            why="Reliable",
            alternatives_rejected={"MySQL": "Less features", "SQLite": "No scale"},
            tradeoffs=["Heavier"],
            failure_conditions=["OOM"],
            confidence=ConfidenceScore(
                score=0.95,
                fact_references=["ref1"],
                unverified_assumptions=["asm1", "asm2"],
                risk_penalty=0.2,
                justification="test",
            ),
        )
        calibrate_confidence_in_place(td)
        # (1/3) * (0.8) ≈ 0.267
        assert td.confidence.score == pytest.approx(0.267, abs=0.01)

    def test_list_of_models(self):
        scores = [
            ConfidenceScore(
                score=0.99,
                fact_references=["a", "b", "c", "d"],
                unverified_assumptions=[],
                risk_penalty=0.0,
                justification="x",
            ),
            ConfidenceScore(
                score=0.1,
                fact_references=[],
                unverified_assumptions=["x"],
                risk_penalty=0.0,
                justification="y",
            ),
        ]
        calibrate_confidence_in_place(scores)
        assert scores[0].score == pytest.approx(0.98)
        assert scores[1].score == pytest.approx(0.05)


# ══════════════════════════════════════════════════════════════════════════════
# 5. PROMPT BUILDER TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestPromptBuilders:
    def test_diagnostic_retry_contains_errors(self):
        prompt = build_diagnostic_retry_prompt(
            original_prompt="Analyse this project.",
            raw_response='{"bad": true}',
            validation_errors=["field 'x' is required", "score: > 1.0"],
        )
        assert "VALIDATION FAILED" in prompt
        assert "field 'x' is required" in prompt
        assert "score: > 1.0" in prompt

    def test_lint_retry_contains_violations(self):
        prompt = build_lint_retry_prompt(
            original_prompt="Analyse this project.",
            raw_response='{"ok": true}',
            lint_violations=["MVP features exceed 5"],
        )
        assert "LINT VIOLATIONS" in prompt
        assert "MVP features exceed 5" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# 6. AGENT EXECUTION HARNESS INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


def _make_valid_product_spec_json() -> str:
    """Return a valid ProductSpecification JSON with ≥2 rejected alts
    in any TechDecision (there are none here, so no lint issue)."""
    return json.dumps({
        "problem_statement": "Automate code review.",
        "target_users": ["Engineers"],
        "user_personas": [{"name": "Alice", "role": "Lead"}],
        "core_value_proposition": "Save 60% review time.",
        "functional_requirements": ["GitHub integration"],
        "mvp_features": ["PR analysis", "Dashboard"],
        "future_scope": ["Multi-repo"],
        "non_goals": ["Code generation"],
        "success_metrics": [{"metric": "Latency", "target": "<2h"}],
        "product_risks": ["Adoption friction"],
    })


def _make_harness(llm_client, **kwargs) -> AgentExecutionHarness:
    """Helper to create a harness with default settings."""
    defaults = {
        "target_schema": ProductSpecification,
        "agent_name": "TestProductManager",
        "system_prompt": "You are a product manager. Analyse the idea.",
        "llm_client": llm_client,
    }
    defaults.update(kwargs)
    return AgentExecutionHarness(**defaults)


class TestAgentExecutionHarness:
    """Integration tests for the AgentExecutionHarness class."""

    @pytest.mark.asyncio
    async def test_retries_keep_only_latest_failure(self):
        replies = ['{"first_failure":true}', '{"second_failure":true}', _make_valid_product_spec_json()]
        prompts = []

        def model(prompt):
            prompts.append(prompt)
            return replies[len(prompts) - 1]

        result = await _make_harness(model).execute({'raw_idea': 'Keep this requirement'}, max_retries=2)
        assert result.success
        assert 'first_failure' in prompts[1]
        assert 'first_failure' not in prompts[2]
        assert 'second_failure' in prompts[2]
        assert prompts[2].count('--- CONTEXT ---') == 1
        assert 'Keep this requirement' in prompts[2]

    @pytest.mark.asyncio
    async def test_truncation_is_not_retried_unchanged(self):
        from app.agents.model_client import ModelOutputTruncatedError
        model = MagicMock(side_effect=ModelOutputTruncatedError('Output truncated'))
        with pytest.raises(ModelOutputTruncatedError):
            await _make_harness(model).execute({'raw_idea': 'Build notes'}, max_retries=2)
        assert model.call_count == 1

    @pytest.mark.asyncio
    async def test_successful_first_pass(self):
        """Mocked Gemini returns valid JSON on first call → success."""
        valid_json = _make_valid_product_spec_json()
        mock_llm = MagicMock(return_value=valid_json)
        harness = _make_harness(mock_llm)

        result = await harness.execute(
            context_data={"raw_idea": "Build X", "intake_qa": {"Q1": "What?"}},
            max_retries=2,
        )

        assert result.success is True
        assert result.attempts == 1
        assert isinstance(result.output, ProductSpecification)
        assert result.output.problem_statement == "Automate code review."
        assert len(result.raw_responses) == 1

    @pytest.mark.asyncio
    async def test_malformed_json_recovers_on_retry(self):
        """First call returns malformed JSON, second returns valid → success."""
        valid_json = _make_valid_product_spec_json()
        bad_json = '{"problem_statement": "X"}'  # missing required fields

        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else valid_json

        harness = _make_harness(mock_llm)

        result = await harness.execute(
            context_data={"raw_idea": "Build X"},
            max_retries=2,
        )

        assert result.success is True
        assert result.attempts == 2
        assert len(result.raw_responses) == 2

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Every attempt returns invalid JSON → failure."""
        bad_json = '{"bad": true}'
        mock_llm = MagicMock(return_value=bad_json)
        harness = _make_harness(mock_llm)

        result = await harness.execute(
            context_data={"raw_idea": "Build X"},
            max_retries=1,
        )

        assert result.success is False
        assert result.attempts == 2
        assert len(result.validation_errors) > 0

    @pytest.mark.asyncio
    async def test_custom_lint_rule_triggers_retry(self):
        """Schema-valid output that fails a custom lint rule gets retried."""
        valid_json = _make_valid_product_spec_json()
        lint_fired = [False]

        def custom_lint(model: ProductSpecification) -> List[str]:
            if lint_fired[0]:
                return []
            lint_fired[0] = True
            return ["Custom rule violated"]

        mock_llm = MagicMock(return_value=valid_json)
        harness = _make_harness(mock_llm, extra_lint_rules=[custom_lint])

        result = await harness.execute(
            context_data={"raw_idea": "Build X"},
            max_retries=2,
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_builtin_lint_tech_decision_alternatives(self):
        """Built-in lint should catch TechDecision with < 2 alternatives.

        Since ProductSpecification has no TechDecision fields, this test
        uses EngineeringSpecification via a mock that returns data with
        a single rejected alternative.
        """
        from app.models.schemas import EngineeringSpecification

        spec_dict = {
            "system_architecture_pattern": "Monolith",
            "frontend_architecture": _make_tech_decision(
                category="Frontend", selected="React",
                alternatives_rejected={"Vue": "Less popular"},  # only 1!
            ),
            "backend_architecture": _make_tech_decision(category="Backend"),
            "database_primary": _make_tech_decision(category="DB"),
            "api_protocol": _make_tech_decision(category="API"),
            "storage_strategy": _make_tech_decision(category="Storage"),
            "observability_stack": {"logging": "Loki"},
            "mermaid_diagram": "graph TD; A-->B;",
            "scalability_limits_and_bottlenecks": ["Write bottleneck"],
        }
        bad_json = json.dumps(spec_dict)

        # Fix on second attempt
        fixed_spec = spec_dict.copy()
        fixed_spec["frontend_architecture"] = _make_tech_decision(
            category="Frontend", selected="React",
        )  # has 2 alts
        good_json = json.dumps(fixed_spec)

        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return bad_json if call_count == 1 else good_json

        harness = AgentExecutionHarness(
            target_schema=EngineeringSpecification,
            agent_name="TestEngineer",
            system_prompt="Design the architecture.",
            llm_client=mock_llm,
        )

        result = await harness.execute(context_data={}, max_retries=2)

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_llm_exception_handled_with_retry(self):
        """LLM raises on first call, succeeds on second."""
        valid_json = _make_valid_product_spec_json()
        call_count = 0

        def flaky_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Gemini API timeout")
            return valid_json

        harness = _make_harness(flaky_llm)

        result = await harness.execute(
            context_data={"raw_idea": "Build X"},
            max_retries=2,
        )

        assert result.success is True
        assert result.attempts == 2
        assert "<LLM_ERROR:" in result.raw_responses[0]

    @pytest.mark.asyncio
    async def test_prompt_includes_json_schema(self):
        """The prompt sent to the LLM must contain the target JSON schema."""
        captured_prompts: List[str] = []
        valid_json = _make_valid_product_spec_json()

        def spy_llm(prompt: str) -> str:
            captured_prompts.append(prompt)
            return valid_json

        harness = _make_harness(spy_llm)
        await harness.execute(context_data={"raw_idea": "Build X"})

        prompt = captured_prompts[0]
        assert "JSON Schema" in prompt
        assert "problem_statement" in prompt  # field from schema
        assert "CONTEXT" in prompt

    @pytest.mark.asyncio
    async def test_zero_retries_single_attempt(self):
        """max_retries=0 means only the initial call."""
        bad_json = '{"bad": true}'
        mock_llm = MagicMock(return_value=bad_json)
        harness = _make_harness(mock_llm)

        result = await harness.execute(
            context_data={"raw_idea": "Build X"},
            max_retries=0,
        )

        assert result.success is False
        assert result.attempts == 1
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_harness_result_defaults(self):
        """HarnessResult has sensible defaults."""
        r = HarnessResult()
        assert r.success is False
        assert r.output is None
        assert r.attempts == 0
        assert r.validation_errors == []
        assert r.lint_violations == []
        assert r.raw_responses == []

    @pytest.mark.asyncio
    async def test_confidence_calibrated_in_output(self):
        """After harness execution, ConfidenceScore values should be
        recalculated using the empirical formula, not self-reported."""
        from app.models.schemas import EngineeringSpecification

        spec_dict = {
            "system_architecture_pattern": "Monolith",
            "frontend_architecture": _make_tech_decision(
                category="Frontend", selected="React",
                confidence=_make_confidence(
                    score=0.99,  # inflated — should be recalculated
                    fact_references=["ref1", "ref2"],
                    unverified_assumptions=["asm1"],
                    risk_penalty=0.1,
                ),
            ),
            "backend_architecture": _make_tech_decision(category="Backend"),
            "database_primary": _make_tech_decision(category="DB"),
            "api_protocol": _make_tech_decision(category="API"),
            "storage_strategy": _make_tech_decision(category="Storage"),
            "observability_stack": {"logging": "Loki"},
            "mermaid_diagram": "graph TD; A-->B;",
            "scalability_limits_and_bottlenecks": ["Write bottleneck"],
        }

        mock_llm = MagicMock(return_value=json.dumps(spec_dict))
        harness = AgentExecutionHarness(
            target_schema=EngineeringSpecification,
            agent_name="TestEngineer",
            system_prompt="Design the architecture.",
            llm_client=mock_llm,
        )

        result = await harness.execute(context_data={})
        assert result.success is True

        # Frontend confidence: (2/3) * (0.9) ≈ 0.6, NOT 0.99
        fe = result.output.frontend_architecture
        assert fe.confidence.score == pytest.approx(0.6, abs=0.01)
        assert fe.confidence.score != pytest.approx(0.99)
