"""Bounded section generation, followed by the original whole-report validators."""
import copy
from functools import partial
from pydantic import create_model, ValidationError
from app.harness.base_harness import AgentExecutionHarness, HarnessResult, calibrate_confidence_in_place


async def execute_sections(harness, context, groups, output_tokens=2048):
    fields = harness.target_schema.model_fields
    names = [name for group in groups for name in group]
    if len(names) != len(set(names)) or set(names) != set(fields):
        raise ValueError('Section groups must cover every report field exactly once')
    combined = {}
    result = HarnessResult()
    for index, group in enumerate(groups):
        section = create_model(f'{harness.target_schema.__name__}Section{index + 1}',
            **{name: (fields[name].annotation, copy.deepcopy(fields[name])) for name in group})
        child = AgentExecutionHarness(target_schema=section,
            agent_name=f'{harness.agent_name}/section-{index + 1}',
            system_prompt=harness.system_prompt + '\nThis is one section of the report. Return only fields in this section schema. Keep explanations concise; preserve all user constraints.',
            llm_client=partial(harness.llm_client, output_tokens=output_tokens))
        section_context = {**context, 'completed_sections': combined}
        section_result = await child.execute(context_data=section_context, max_retries=1)
        result.attempts += section_result.attempts
        result.raw_responses.extend(section_result.raw_responses)
        if not section_result.success:
            result.validation_errors = section_result.validation_errors
            result.lint_violations = section_result.lint_violations
            return result
        combined.update(section_result.output.model_dump(mode='json'))
    try:
        validated = harness.target_schema.model_validate(combined)
    except ValidationError as exc:
        result.validation_errors = [str(exc)]
        return result
    result.lint_violations = [v for rule in harness.lint_rules for v in rule(validated)]
    if result.lint_violations:
        return result
    calibrate_confidence_in_place(validated)
    result.output, result.success = validated, True
    return result
