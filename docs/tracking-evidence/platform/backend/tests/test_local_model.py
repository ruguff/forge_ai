import json
import httpx
import pytest
from app.agents.model_client import LocalModelClient, GeminiModelClient, ModelUnavailableError, ModelBudgetExceeded
from app.config import get_settings

def test_local_provider_without_cloud_key(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'lmstudio')
    monkeypatch.setenv('GEMINI_API_KEY', '')
    get_settings.cache_clear()
    try:
        model = GeminiModelClient()
        assert isinstance(model, LocalModelClient)
        assert model._payload('JSON please')['model'] == 'nvidia/nemotron-3-nano-4b'
        schema = {'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok']}
        payload = model._payload('Schema:\n```json\n' + json.dumps(schema) + '\n```')
        assert payload['response_format']['json_schema']['schema'] == schema
        assert model._read(httpx.Response(200, json={'choices':[{'message':{'content':'{"ok":true}'}}], 'usage':{'prompt_tokens':5,'completion_tokens':4}})) == '{"ok":true}'
        assert model.usage()['output_tokens'] == 4
        with pytest.raises(ModelUnavailableError, match='truncated'):
            model._read(httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{'}}]}))
        model.calls = model.settings.MAX_MODEL_CALLS
        with pytest.raises(ModelBudgetExceeded):
            model._payload('another request')
    finally:
        get_settings.cache_clear()

def test_local_url_rejects_external_server(monkeypatch):
    monkeypatch.setenv('LOCAL_MODEL_BASE_URL', 'http://example.com/v1')
    get_settings.cache_clear()
    try:
        with pytest.raises(ModelUnavailableError,match='loopback'):
            LocalModelClient()
    finally:
        get_settings.cache_clear()


def test_local_reasoning_control_and_truncation_diagnostics(monkeypatch):
    monkeypatch.setenv('LOCAL_MODEL_REASONING_EFFORT', 'none')
    monkeypatch.setenv('MAX_MODEL_OUTPUT_TOKENS', '4096')
    get_settings.cache_clear()
    try:
        model = LocalModelClient()
        assert model._payload('Return JSON')['reasoning_effort'] == 'none'
        response = httpx.Response(200, json={
            'choices': [{'finish_reason': 'length', 'message': {'content': '{'}}],
            'usage': {'completion_tokens': 4096, 'completion_tokens_details': {'reasoning_tokens': 1000}},
        })
        with pytest.raises(ModelUnavailableError, match='reasoning: 1000'):
            model._read(response)
        assert model.output_tokens == 4096
    finally:
        get_settings.cache_clear()


def test_compact_prompt_preserves_json_and_checks_actual_size(monkeypatch):
    monkeypatch.setenv('MAX_MODEL_INPUT_CHARS', '700')
    get_settings.cache_clear()
    try:
        model = LocalModelClient()
        context = {'requirements': [{'id': str(i), 'text': 'Keep  two spaces and a newline\ninside values.'} for i in range(5)]}
        prompt = '--- CONTEXT ---\n' + json.dumps(context, indent=8) + '\n--- END CONTEXT ---'
        assert len(prompt) > 700
        payload = model._payload(prompt)
        compacted = payload['messages'][1]['content']
        assert len(compacted) < 700
        assert json.loads(compacted.split('--- CONTEXT ---')[1].split('--- END CONTEXT ---')[0]) == context
        before = model.calls
        with pytest.raises(ModelBudgetExceeded, match='No request was sent'):
            model._payload('x' * 701)
        assert model.calls == before
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_measured_context_rejects_overflow_without_model_call(monkeypatch):
    from app.agents import local_context
    async def measure(*args):
        return 4000, 8192
    monkeypatch.setattr(local_context, 'measure_context', measure)
    monkeypatch.setenv('MAX_MODEL_OUTPUT_TOKENS', '4096')
    get_settings.cache_clear()
    try:
        model = LocalModelClient()
        with pytest.raises(ModelBudgetExceeded, match='No inference request was sent'):
            await model.generate('Small text can still have a large measured token count')
        assert model.calls == 0
        assert model.last_context['prompt_tokens'] == 4000
        async def fits(*args):
            return 3000, 8192
        monkeypatch.setattr(local_context, 'measure_context', fits)
        await model._check_context(model._payload('A fitting prompt'))
    finally:
        get_settings.cache_clear()
