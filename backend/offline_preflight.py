"""Read-only local service and generated-code sandbox readiness report."""
import json
import httpx
from app.config import get_settings
from app.execution.sandbox.executor import SafeCommandExecutor

settings = get_settings()
report = {'provider': settings.LLM_PROVIDER, 'model': settings.LOCAL_MODEL_NAME,
          'output_limit': settings.MAX_MODEL_OUTPUT_TOKENS,
          'input_character_guard': settings.MAX_MODEL_INPUT_CHARS,
          'reasoning_effort': settings.LOCAL_MODEL_REASONING_EFFORT}
with httpx.Client(timeout=5, trust_env=False) as client:
    for name, url in [('backend', 'http://127.0.0.1:8000/'), ('frontend', 'http://127.0.0.1:3000/'),
                      ('models', settings.LOCAL_MODEL_BASE_URL.removesuffix('/v1') + '/api/v1/models')]:
        try:
            response = client.get(url)
            response.raise_for_status()
            report[name] = response.json() if name != 'frontend' else {'status': response.status_code}
        except httpx.HTTPError as exc:
            report[name] = {'error': str(exc)}
available, reason = SafeCommandExecutor('.').preflight()
report['sandbox'] = {'available': available, 'reason': reason}
print(json.dumps(report, indent=2))
