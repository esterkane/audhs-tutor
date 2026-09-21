---
name: llm-routing
description: TaskClass → provider/model routing table, ModelProvider conventions, in-app budget and prompt-caching layout. Claude loads this whenever it adds an LLM call, edits models_ai/, or picks a model.
user-invocable: true
---
# LLM routing (ADR-0001)

`ModelProvider` interface (`backend/app/models_ai/provider.py`, `complete(...) → ProviderResult`). Implementations: `OllamaProvider`, `ClaudeProvider` (LiteLLM SDK; no proxy), `FakeProvider` (tests). `MlxProvider` (TTS/voice) is planned for Stage 5 — not present. Calls go through `models_ai/gateway.py` (`ModelGateway`: routing, budget, `model_call` rows); providers are built by `models_ai/factory.py`.

**Model registry (ADR-0010)**: models are rows in `model_registry` managed by `models_ai/manage.py`, driven by `make models args="…"` → `scripts/models.py` (`seed | list | search-hf <query> [--gguf|--mlx] | info <repo_id> | add <source> <repo_id> [--file|--tag] [--role] | pull <id> | bench <id> | rm <id> | assign <task> <id>`) or the `/models` screen (`/api/models`, background pull/bench jobs). Sources: `ollama_library`, `huggingface_gguf` (→ Modelfile → `ollama create`), `huggingface_mlx` (snapshot under `data/models/mlx/`), `huggingface_fastembed` (cross-encoders), `hosted`. A model must be `ready` and have `benchmark_json` before it can be assigned. Pulls are learner-initiated (`pull` is in the *ask* permission list). `routing.py` resolves `TaskClass → registry id` from `routing_profiles.yaml` defaults + `learner_preference("routing.<task>")` overrides; every `model_call` records the registry id. Never hardcode a model name anywhere else.

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
| `rerank` | local | `ms-marco-minilm-l6` (fastembed cross-encoder) | fused order (no rerank) |
| `stt` (ingest transcription; voice later) | local | `whisper-large-v3-turbo` (MLX, `mlx-whisper` extra) | file reported as skipped |
| `vision` (slide images) | local | `gemma3-12b` (multimodal) | file reported as skipped |

Rules
- Local by default; adding a hosted TaskClass needs an ADR. Downloads are learner-initiated (`pull` is in the *ask* permission list).
- `budget.py` (P6): daily hosted cap from `.env` (`DAILY_BUDGET_USD`). Every hosted attempt **reserves** its worst case first (prompt chars/4 + `max_tokens` at the registry price; one lock per app process on `app.state.budget_lock`), runs, then **reconciles** to the reported/estimated cost; a failed call with no usage settles at the reserved amount (`cost_status=unknown`, never free); reservations older than 10 min expire. What the cap sees = reported + estimated + legacy + unknown-at-reserved + open reservations. When exceeded: `outcome=blocked` row, fall back to local, emit `degraded`, the session screen says "local model: the daily hosted budget is used up". Cost view: `GET /api/models/costs` (`models_ai/usage.py`), Models screen › Hosted spend.
- Prompt caching (Anthropic): byte-stable `TutorPolicy` first, then structured preferences; per-turn sections after. No timestamps in the cached prefix.
- Structured output via Instructor; local models use JSON mode, Claude tool mode; one attempt per provider call, the gateway repairs twice, the third invalid reply → escalate one tier + `invalid_output(attempts=3)` (P6).
- Every call: `metadata={task, session_id, skill_id, prompt_version, request_id}`; one `model_call` row **per provider attempt** (`request_id`, `attempt`, unique `idempotency_key`, `outcome ok|error|invalid_output|cancelled|partial|blocked`, `usage_source reported|estimated|unavailable|legacy`, `cost_status free|reported|estimated|unknown|legacy`, `reserved_usd`). Streams ask for the provider's final usage chunk (`stream_options.include_usage`); without one, tokens are chars/4 and the row says `estimated`. Structured output: one attempt per provider call, up to two gateway repairs (each a row; the repair turn carries validator messages only), then `invalid_output(attempts=3)` + escalate one tier — three invalid replies, not two as before P6.
- Local models log `cost=0` explicitly; tokens are still recorded.
- STT is a registry model like any other (`TaskClass.STT`, runtime `mlx`, used by `knowledge/ingest/media.py`; the voice loop will reuse it). TTS (Kokoro) is Stage 5 and will get its own TaskClass via ADR. The LLM turn in the voice loop uses `chat_fast`.
- The daily cap is a *pre-call threshold*: `Budget.check` compares spend so far with the cap; projected cost and reservations are P6 (`docs/IMPROVEMENT-PLAN.md`).
