---
name: llm-routing
description: TaskClass → provider/model routing table, ModelProvider conventions, in-app budget and prompt-caching layout. Claude loads this whenever it adds an LLM call, edits models_ai/, or picks a model.
user-invocable: true
---
# LLM routing (ADR-0001)

`ModelProvider` interface (`backend/app/models_ai/provider.py`): `complete(task, messages, response_model=None, stream=False) → ProviderResult`. Implementations: `OllamaProvider`, `MlxProvider` (STT/TTS), `ClaudeProvider` (LiteLLM SDK; no proxy).

**Model registry (ADR-0010)**: models are rows in `model_registry` added via `scripts/models.py` (`search-hf <query>`, `add <source> <repo_id> [--file|--tag]`, `pull <id>`, `bench <id>`, `assign <task> <id>`, `rm <id>`) or the Settings › Models screen. Sources: Ollama library, Hugging Face GGUF (→ Modelfile → `ollama create`), `mlx-community` safetensors, hosted. A model must have `benchmark_json` before it can be assigned. `routing.py` resolves `TaskClass → registry id` from `routing_profiles.yaml` defaults + `learner_preference("routing.<task>")` overrides; every `model_call` records the registry id. Never hardcode a model name anywhere else.

| TaskClass | Route | Default registry entry in `routing_profiles.yaml` (replaceable) | Fallback |
|---|---|---|---|
| `format`, `summarize`, `query_expand`, `gen_items` | local | `gemma3:12b` (Q4) via Ollama | `llama3.1:8b` |
| `chat_fast` (voice, low-capacity) | local | `llama3.1:8b` | — |
| `explain_simple`, `hint` | local | `gemma3:12b` / `qwen3:14b` (≥ 15 tok/s) | `hosted-medium` |
| `code_local` | local | `qwen3-coder:30b-a3b` | `hosted-strong` |
| `grade_simple` | local (after deterministic + rubric levels) | `gemma3:12b` | `hosted-medium` |
| `grade_rubric` (free text / explain-back / transfer) | hosted | Claude Sonnet | `hosted-medium` |
| `tutor_deep`, `socratic`, `challenge`, `code_review`, `conflict_resolution` | hosted | Claude Sonnet | `local` (degraded, flagged) |
| `tutor_medium` | hosted | Claude Haiku | `local` |
| `judge` (evals) | hosted | Claude Haiku | `hosted-strong` |
| `embed` | local | `nomic-embed-text` (or `qwen3-embedding:0.6b` multilingual) | — |

Rules
- Local by default; adding a hosted TaskClass needs an ADR. Downloads are learner-initiated (`pull` is in the *ask* permission list).
- `budget.py`: daily hosted cap from `.env` (`DAILY_BUDGET_USD`); when exceeded, fall back to local, emit `degraded` event, surface a banner.
- Prompt caching (Anthropic): byte-stable `TutorPolicy` first, then structured preferences; per-turn sections after. No timestamps in the cached prefix.
- Structured output via Instructor; local models use JSON mode; two validation failures → escalate one tier + `invalid_output` event.
- Every call: `metadata={task, session_id, skill_id, prompt_version}`; write `model_call` with tokens/cost/latency/cached.
- Local models log `cost=0` explicitly; tokens are still recorded.
- STT/TTS bypass providers (direct whisper/Kokoro); the LLM turn in the voice loop still uses `chat_fast`.
