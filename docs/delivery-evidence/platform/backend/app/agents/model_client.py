"""Shared, bounded model adapter. Missing credentials never imply AI success."""
import asyncio
import json
import re
from app.config import get_settings


class ModelUnavailableError(RuntimeError):
    pass


class ModelBudgetExceeded(RuntimeError):
    pass


class ModelOutputTruncatedError(ModelUnavailableError):
    """Retrying the same prompt and output allowance cannot ensure completion."""
    pass


class GeminiModelClient:
    def __new__(cls):
        settings = get_settings()
        if settings.LLM_PROVIDER == "lmstudio":
            return LocalModelClient()
        if settings.LLM_PROVIDER != "gemini":
            raise ModelUnavailableError("Unsupported LLM_PROVIDER. Use gemini or lmstudio.")
        return super().__new__(cls)

    def __init__(self):
        from google import genai
        self.settings = get_settings()
        key = self.settings.GEMINI_API_KEY
        if not key or key.startswith("mock"):
            raise ModelUnavailableError("Set GEMINI_API_KEY in backend/.env to run AI agents.")
        self.client = genai.Client(api_key=key, http_options={"timeout": int(self.settings.MODEL_TIMEOUT_SECONDS * 1000)})
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    async def generate(self, prompt: str) -> str:
        if self.calls >= self.settings.MAX_MODEL_CALLS:
            raise ModelBudgetExceeded("Project model-call budget exhausted.")
        if len(prompt) > self.settings.MAX_MODEL_INPUT_CHARS:
            raise ModelBudgetExceeded("Model input exceeds the configured context budget.")
        self.calls += 1
        response = await asyncio.wait_for(
            self.client.aio.models.generate_content(
                model=self.settings.GEMINI_MODEL, contents=prompt,
                config={"response_mime_type": "application/json",
                        "max_output_tokens": self.settings.MAX_MODEL_OUTPUT_TOKENS},
            ), timeout=self.settings.MODEL_TIMEOUT_SECONDS,
        )
        usage = response.usage_metadata
        if usage:
            self.input_tokens += usage.prompt_token_count or 0
            self.output_tokens += usage.candidates_token_count or 0
        if not response.text:
            raise ModelUnavailableError("Model returned no output.")
        return response.text

    def generate_sync(self, prompt: str) -> str:
        if self.calls >= self.settings.MAX_MODEL_CALLS or len(prompt) > self.settings.MAX_MODEL_INPUT_CHARS:
            raise ModelBudgetExceeded("Coding model budget exceeded.")
        self.calls += 1
        response = self.client.models.generate_content(model=self.settings.GEMINI_MODEL, contents=prompt,
            config={"response_mime_type": "application/json", "max_output_tokens": self.settings.MAX_MODEL_OUTPUT_TOKENS})
        if response.usage_metadata:
            self.input_tokens += response.usage_metadata.prompt_token_count or 0
            self.output_tokens += response.usage_metadata.candidates_token_count or 0
        if not response.text:
            raise ModelUnavailableError("Coding model returned no output.")
        return response.text

    def usage(self):
        return {"model": self.settings.GEMINI_MODEL, "calls": self.calls,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "confidence_calibrated": False}


class LocalModelClient:
    """OpenAI-compatible localhost adapter; never falls back to cloud calls."""
    def __init__(self):
        from urllib.parse import urlparse
        self.settings = get_settings()
        address = urlparse(self.settings.LOCAL_MODEL_BASE_URL)
        if address.scheme != "http" or address.hostname not in {"localhost", "127.0.0.1", "::1"} or address.username or address.password:
            raise ModelUnavailableError("Local model URL must be an HTTP loopback address.")
        self.calls = self.input_tokens = self.output_tokens = 0

    def _payload(self, prompt):
        if self.calls >= self.settings.MAX_MODEL_CALLS:
            raise ModelBudgetExceeded(f"Local model call budget exhausted ({self.calls}/{self.settings.MAX_MODEL_CALLS}).")
        original_size = len(prompt)
        # Compact JSON formatting only: retain every requirement and schema constraint.
        def compact(match):
            try:
                return match.group(1) + json.dumps(json.loads(match.group(2)), ensure_ascii=False, separators=(',', ':')) + match.group(3)
            except json.JSONDecodeError:
                return match.group(0)
        prompt = re.sub(r'(```json\s*)(.*?)(\s*```)', compact, prompt, flags=re.DOTALL)
        prompt = re.sub(r'(--- CONTEXT ---\s*)(.*?)(\s*--- END CONTEXT ---)', compact, prompt, flags=re.DOTALL)
        if len(prompt) > self.settings.MAX_MODEL_INPUT_CHARS:
            raise ModelBudgetExceeded(
                f"Local prompt is too large: {len(prompt):,} characters after lossless JSON compaction "
                f"({original_size:,} originally); limit {self.settings.MAX_MODEL_INPUT_CHARS:,}. "
                "No request was sent to LM Studio. Reduce project scope or configure a larger input budget supported by the loaded context.")
        schema = {"type": "object", "additionalProperties": True}
        # Existing agent prompts already include their Pydantic JSON schema.
        # Supply it to the local runtime as well so decoding enforces field types.
        for block in re.findall(r"```json\s*(.*?)\s*```", prompt, flags=re.DOTALL):
            try:
                candidate = json.loads(block)
                if isinstance(candidate, dict) and candidate.get("type") == "object" and "properties" in candidate:
                    schema = candidate
            except json.JSONDecodeError:
                continue
        payload = {"model": self.settings.LOCAL_MODEL_NAME,
                "messages": [{"role": "system", "content": "Return only valid JSON matching the requested schema. No markdown fences, commentary, or reasoning outside JSON."},
                             {"role": "user", "content": prompt}],
                "temperature": 0.1, "max_tokens": self.settings.MAX_MODEL_OUTPUT_TOKENS,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": "projectforge_response", "strict": True,
                    "schema": schema}}, "stream": False}
        # Optional: only set this for a runtime/model that supports the setting.
        # Nemotron otherwise spends the same output allowance on reasoning and JSON.
        if self.settings.LOCAL_MODEL_REASONING_EFFORT:
            payload["reasoning_effort"] = self.settings.LOCAL_MODEL_REASONING_EFFORT
        return payload

    def _read(self, response, output_tokens=None):
        if response.status_code != 200:
            raise ModelUnavailableError(f"Local model HTTP {response.status_code}: {response.text[:600]}")
        body = response.json()
        usage = body.get("usage", {})
        self.input_tokens += usage.get("prompt_tokens", 0)
        self.output_tokens += usage.get("completion_tokens", 0)
        choice = body.get("choices", [{}])[0]
        if choice.get("finish_reason") == "length":
            reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            raise ModelOutputTruncatedError(
                f"Local model output was truncated at an output allowance of {output_tokens or self.settings.MAX_MODEL_OUTPUT_TOKENS} tokens "
                f"(reported completion: {usage.get('completion_tokens', 0)}, reasoning: {reasoning}). "
                "No partial JSON was accepted. Adjust local reasoning/output settings within the loaded context limit.")
        content = choice.get("message", {}).get("content")
        if not content:
            raise ModelUnavailableError("Local model returned no JSON content.")
        return content

    async def _check_context(self, payload):
        from app.agents.local_context import measure_context
        try:
            prompt_tokens, context_tokens = await asyncio.wait_for(measure_context(
                self.settings.LOCAL_MODEL_BASE_URL, self.settings.LOCAL_MODEL_NAME,
                payload['messages']), timeout=20)
        except Exception as exc:
            raise ModelUnavailableError(f"Cannot measure local model context: {exc}") from exc
        # Tokenize the runtime's chat template; reserve extra room for differences
        # between SDK formatting and HTTP inference settings/structured decoding.
        margin = 256
        self.last_context = {'prompt_tokens': prompt_tokens, 'context_tokens': context_tokens,
                             'reserved_output_tokens': payload['max_tokens'], 'margin_tokens': margin}
        if prompt_tokens + payload['max_tokens'] + margin > context_tokens:
            raise ModelBudgetExceeded(
                f"Local context budget exceeded: {prompt_tokens} measured prompt tokens + "
                f"{payload['max_tokens']} reserved output + {margin} margin > {context_tokens} loaded context. "
                "Split this stage into smaller tasks. No inference request was sent.")

    async def generate(self, prompt, *, output_tokens=None):
        import httpx
        payload = self._payload(prompt)
        if output_tokens is not None:
            payload['max_tokens'] = min(self.settings.MAX_MODEL_OUTPUT_TOKENS, output_tokens)
        await self._check_context(payload)
        self.calls += 1
        try:
            async with httpx.AsyncClient(timeout=self.settings.MODEL_TIMEOUT_SECONDS, trust_env=False) as client:
                response = await client.post(self.settings.LOCAL_MODEL_BASE_URL.rstrip('/') + '/chat/completions', json=payload)
            return self._read(response, payload['max_tokens'])
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(f"Local model request timed out after {self.settings.MODEL_TIMEOUT_SECONDS:g}s. Reduce task size or adjust the measured timeout budget.") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Cannot reach LM Studio or request timed out: {exc}") from exc

    def generate_sync(self, prompt, *, output_tokens=None):
        import httpx
        payload = self._payload(prompt)
        if output_tokens is not None:
            payload['max_tokens'] = min(self.settings.MAX_MODEL_OUTPUT_TOKENS, output_tokens)
        asyncio.run(self._check_context(payload))
        self.calls += 1
        try:
            with httpx.Client(timeout=self.settings.MODEL_TIMEOUT_SECONDS, trust_env=False) as client:
                response = client.post(self.settings.LOCAL_MODEL_BASE_URL.rstrip('/') + '/chat/completions', json=payload)
            return self._read(response, payload['max_tokens'])
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(f"Local model request timed out after {self.settings.MODEL_TIMEOUT_SECONDS:g}s. Reduce task size or adjust the measured timeout budget.") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Cannot reach LM Studio or request timed out: {exc}") from exc

    def usage(self):
        return {"provider": "lmstudio", "model": self.settings.LOCAL_MODEL_NAME,
                "calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "confidence_calibrated": False}
