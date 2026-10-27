import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.agents import pipeline
from app.models.schemas import ProjectState, ProjectContext, ProductSpecification
from app.agents.model_client import ModelUnavailableError
from tests.test_agents import _make_valid_product_json


@pytest.mark.asyncio
async def test_failed_analysis_reuses_only_unchanged_validated_stages(monkeypatch):
    state = ProjectState(project_id='RECOVERY', status='INTAKE', raw_idea='Tasks', intake_qa={})
    context = ProjectContext(project_id='RECOVERY', raw_request='Tasks')
    product = ProductSpecification.model_validate(json.loads(_make_valid_product_json()))
    analyze = AsyncMock(return_value=SimpleNamespace(success=True, output=product, attempts=1))
    monkeypatch.setattr(pipeline, 'ProductAgent', lambda **kw: SimpleNamespace(analyze=analyze))
    failure = AsyncMock(side_effect=ModelUnavailableError('offline model stopped'))
    monkeypatch.setattr(pipeline, 'AIMLAgent', lambda **kw: SimpleNamespace(analyze=failure))
    emit = AsyncMock()
    model = SimpleNamespace(generate=AsyncMock())
    for resume in (False, True):
        with pytest.raises(ModelUnavailableError):
            await pipeline.run_specialists(state, context, model, emit, lambda: None, resume=resume)
    assert analyze.await_count == 1
    assert failure.await_count == 2
    assert any(call.args[0] == 'AGENT_RECOVERED' for call in emit.await_args_list)
    context.version += 1
    with pytest.raises(ModelUnavailableError):
        await pipeline.run_specialists(state, context, model, emit, lambda: None, resume=True)
    assert analyze.await_count == 2
