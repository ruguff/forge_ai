# ProjectForge with local Nemotron

The backend supports `LLM_PROVIDER=lmstudio` with an OpenAI-compatible local API. It uses the same model for requirement extraction, specialists, specification compilation, source generation and repair, and never falls back to Gemini in this mode. Specialists execute sequentially.

Current settings in backend/.env:

```env
LLM_PROVIDER=lmstudio
LOCAL_MODEL_BASE_URL=http://127.0.0.1:1234/v1
LOCAL_MODEL_NAME=nvidia/nemotron-3-nano-4b
MODEL_TIMEOUT_SECONDS=240
MAX_MODEL_INPUT_CHARS=48000
MAX_MODEL_OUTPUT_TOKENS=4096
LOCAL_MODEL_REASONING_EFFORT=none
LOCAL_CODE_GENERATION_STRATEGY=declarative_crud
PIPELINE_TIMEOUT_SECONDS=1800
```

Start LM Studio's server bound only to localhost:

```powershell
lms server start --port 1234 --bind 127.0.0.1
lms ps
```

Keep one loaded model instance and one concurrent prediction. On the latest check this installation reports 8192 context tokens and parallel=1. Input, output, and chat-template overhead must fit within that context. The model's advertised maximum context is not its loaded context.

The loaded Nemotron supports reasoning on/off. ProjectForge sends `reasoning_effort=none` to LM Studio's OpenAI-compatible API so the output allowance is available for JSON rather than a long reasoning trace. A live probe reported zero reasoning tokens. Leave `LOCAL_MODEL_REASONING_EFFORT` empty for models/runtimes that do not support this parameter; it is not silently retried with a different setting.

The previous 2048-token allowance truncated Engineering: the runtime reported 1576 reasoning tokens, leaving insufficient room for its nested JSON specification. Truncated output remains an error and is never accepted as a completed specification.

As of October 7, the character guard is only a secondary request-size bound. Before inference, the LM Studio Python SDK tokenizes the formatted chat using the already-loaded model and reads its loaded context length. The measured prompt, configured output allowance and a 256-token formatting margin must fit. Measurement failure blocks the call rather than guessing; the check never loads another model. Install updated backend requirements before starting. The SDK is used only against the configured loopback server.

An unchanged truncated request is no longer automatically retried three times. Validation retries retain the original prompt and only the latest failed response and diagnostics. Stage completion events include elapsed time and attempt count.

Restart the backend after configuration changes. Switching back to cloud mode requires `LLM_PROVIDER=gemini` and a valid Gemini key. Existing keys are preserved in .env.

The small output/input budgets may block complex projects. Such failures are reported rather than silently generating templates or using cloud calls. Begin with a small task or notes application. Full website generation quality has not been established by a basic connectivity check. Isolated generated-project execution still requires Docker and its prebuilt image.

## Current source strategy (October 14)

Nemotron 4B failed repeated free-form Python/TSX generation checks, including invalid framework APIs, missing status codes and broken JSX. More output tokens did not address those errors. The default local strategy is now explicitly `declarative_crud`: real local model calls produce requirements, specialist designs and the validated BuildSpec; a deterministic compiler translates that specification into source. `generation_mode=MODEL` identifies the model-designed specification, while `source_generation_strategy=DECLARATIVE_CRUD` identifies the source emitter. Task summaries and generated README files state this distinction. It is not presented as arbitrary model-authored code or an automatic fallback after a failed build.

Supported scope: one entity, integer primary key, text/number fields, unauthenticated list/create/update/delete APIs and one responsive React editor/list page. Auth, relationships, custom endpoints and explicitly requested additional business capabilities are rejected rather than silently omitted. The experimental local model-code path is available by setting `LOCAL_CODE_GENERATION_STRATEGY=model_code`, but it has not passed website verification. Cloud generation remains a separate provider choice; it is never selected automatically.

Current evidence: all six specialist artifacts validated across the baseline and diagnostic continuation; build-spec compilation passed; all 11 source tasks completed; generated frontend static types passed. This is not yet one fresh verified end-to-end run. Docker execution and browser behavior remain unverified.

Verified locally: a basic JSON request completed in 4.94 seconds. A real Product Manager harness request completed in 96 seconds, passed its schema and domain lint on the first attempt, and used 906 input / 1063 output tokens. Backend regression suite: 169 passed. The complete six-agent and generated-website workflow has not yet been validated with this model.

Latest fix validation (October 5, 2026): replaying Engineering against the saved Product and AI/ML outputs from `PROJ-A75D33D78D43` passed schema and domain lint on its first attempt in 92.2 seconds (2574 input / 1421 output tokens). This diagnostic does not change the saved project's status or claim a complete pipeline run. Backend regression suite: 174 passed. Reproducible local diagnostic: run `..\.venv\Scripts\python.exe retest_local_stage.py` from the backend directory; results are written to `docs/local-stage-retest.json`.

Requirement extraction for the same raw request also passed schema and domain lint on the first attempt in 213.5 seconds (1519 input / 3262 output tokens), without the heuristic fallback. This is close to the configured 240-second HTTP timeout; larger requests may still time out or exceed output/context budgets.
