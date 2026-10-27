import json
import pytest
from pydantic import BaseModel
from app.harness.base_harness import AgentExecutionHarness
from app.harness.sections import execute_sections
from app.models.schemas import TechDecision


class Report(BaseModel):
    minimum: int
    maximum: int


@pytest.mark.asyncio
@pytest.mark.parametrize('maximum,success', [(10, True), (1, False)])
async def test_sections_preserve_context_and_enforce_combined_lint(maximum, success):
    calls = []
    async def model(prompt, *, output_tokens):
        calls.append(prompt)
        assert output_tokens == 2048
        assert 'original-requirement-001' in prompt
        return json.dumps({'minimum': 5} if len(calls) == 1 else {'maximum': maximum})
    harness = AgentExecutionHarness(target_schema=Report, agent_name='Report',
        system_prompt='Produce report', llm_client=model,
        extra_lint_rules=[lambda report: [] if report.maximum > report.minimum else ['Invalid range']])
    result = await execute_sections(harness, {'requirements': ['original-requirement-001']}, [['minimum'], ['maximum']])
    assert result.success == success
    assert result.attempts == 2
    if not success:
        assert result.output is None
        assert result.lint_violations == ['Invalid range']


@pytest.mark.asyncio
async def test_sections_cannot_omit_fields():
    harness = AgentExecutionHarness(target_schema=Report, agent_name='Report',
        system_prompt='Produce report', llm_client=lambda prompt: '{}')
    with pytest.raises(ValueError, match='every report field'):
        await execute_sections(harness, {}, [['minimum']])


class DecisionReport(BaseModel):
    decision: TechDecision


@pytest.mark.asyncio
@pytest.mark.parametrize('correct_on_retry', [True, False])
async def test_section_decision_retry_preserves_no_login_and_rejects_missing_alternatives(correct_on_retry):
    calls = []

    async def model(prompt, *, output_tokens):
        calls.append(prompt)
        assert 'Do not add login or accounts' in prompt
        assert 'minProperties' in prompt
        if len(calls) == 2:
            assert 'minimum is 2' in prompt
        alternatives = {'Passwords': 'Login is excluded by the user.'}
        if len(calls) == 2 and correct_on_retry:
            alternatives['OAuth'] = 'External identity services are excluded.'
        return json.dumps({'decision': {
            'category': 'Authentication', 'selected': 'No authentication',
            'why': 'Single-user local scope.', 'alternatives_rejected': alternatives,
            'tradeoffs': ['No account isolation.'],
            'failure_conditions': ['Shared or public deployment requires reassessment.'],
            'confidence': {'score': 0.5, 'fact_references': [],
                           'unverified_assumptions': ['Local use only'],
                           'risk_penalty': 0.1, 'justification': 'User scope.'},
        }})

    harness = AgentExecutionHarness(target_schema=DecisionReport, agent_name='Decision',
        system_prompt='Analyze authentication', llm_client=model)
    result = await execute_sections(harness, {'constraints': 'Do not add login or accounts'},
                                    [['decision']])
    assert result.attempts == 2
    assert result.success is correct_on_retry
    if correct_on_retry:
        assert result.output.decision.selected == 'No authentication'
        assert len(result.output.decision.alternatives_rejected) == 2
    else:
        assert result.output is None
        assert result.lint_violations
