from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents import understanding_service as service
from app.agents.model_client import LocalModelClient, ModelUnavailableError
from app.config import get_settings


@pytest.mark.asyncio
@pytest.mark.parametrize('key', ['', 'mock-tests'])
async def test_local_understanding_does_not_require_cloud_key(monkeypatch, key):
    monkeypatch.setenv('LLM_PROVIDER', 'lmstudio')
    monkeypatch.setenv('GEMINI_API_KEY', key)
    get_settings.cache_clear()
    idea = 'Create a notes application.'
    output = service.generate_heuristic_understanding(idea)
    output.evidence = []
    generation = AsyncMock(return_value=output.model_dump_json())
    monkeypatch.setattr(LocalModelClient, 'generate', generation)

    class Agent:
        def __init__(self, llm_client):
            self.generate = llm_client

        async def analyze_project_idea(self, raw_idea):
            text = await self.generate(raw_idea)
            return SimpleNamespace(success=True, output=type(output).model_validate_json(text))

    monkeypatch.setattr(service, 'ProjectUnderstandingAgent', Agent)
    try:
        result = await service.execute_understanding(idea)
        generation.assert_awaited_once_with(idea)
        assert 'UNDERSTANDING_MODE=MODEL' in result.evidence
        assert not any('HEURISTIC' in item for item in result.evidence)
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_local_failure_keeps_fallback_labelled(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'lmstudio')
    monkeypatch.setenv('GEMINI_API_KEY', '')
    get_settings.cache_clear()
    class UnavailableAgent:
        def __init__(self, llm_client):
            pass

        async def analyze_project_idea(self, idea):
            raise ModelUnavailableError('Local server unavailable')

    monkeypatch.setattr(service, 'ProjectUnderstandingAgent', UnavailableAgent)
    try:
        result = await service.execute_understanding('Create a notes application.')
        assert any('UNDERSTANDING_MODE=HEURISTIC' in item for item in result.evidence)
        assert 'UNDERSTANDING_MODE=MODEL' not in result.evidence
    finally:
        get_settings.cache_clear()
