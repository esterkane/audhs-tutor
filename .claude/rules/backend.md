---
paths:
  - "backend/**"
---
# Backend rules (FastAPI / Python)

Layout: `backend/app/{kernel,orchestrator,knowledge,models_ai,api,db,schemas,core}` + `backend/alembic/` + `backend/tests/`.
- `kernel/` — deterministic, no LLM calls, no HTTP. Owns skill graph, LearningObjects, competency, memory (FSRS), session/checkpoint/preferences, planner, adaptation proposals, experiments. Pure functions + repository calls; 100% unit-testable without network.
- `orchestrator/` — the one tutor loop: `context.py` (ContextPacket builder with budgets), `actions.py` (teaching-action choice), `tutor.py`, `grader.py` (hierarchical), `tools.py` (typed wrappers over kernel). Only place that calls `ModelProvider`.
- `knowledge/` — `repository.py` (`RetrievalRepository` interface), `qdrant_hybrid.py` (production: dense + sparse named vectors, server-side fusion, payload filters, rerank, trust filter), `sqlite_hybrid.py` (tests/fallback), `ingest/`, `provenance.py`. Retrieved text is returned as `ScoredChunk` with provenance; never as raw strings.
- `models_ai/` — `provider.py` (`ModelProvider` interface), `ollama.py`, `mlx.py`, `claude.py` (LiteLLM SDK), `registry.py` + `downloader.py` (HF/Ollama/MLX artifacts, licence, disk), `routing.py` + `routing_profiles.yaml` (TaskClass → registry id; runtime overrides from `learner_preference`), `bench.py`, `budget.py`. Model names never appear outside the registry/profiles. Every call passes `TaskClass` and writes a `model_call` row with the registry id.
- `api/` — thin routers; `Depends(get_db)`, call orchestrator/kernel, return schemas. SSE for tutor stream, WS for voice (later).
- `db/` — SQLAlchemy 2 typed ORM (`Mapped[...]`), `events.py` (append-only writer), `traces.py`. Every learner-scoped table has `learner_id`. IDs ULID, timestamps UTC.
- Structured LLM output via Instructor with a Pydantic model, `max_retries=2`; validation failure → `invalid_output` event and escalation one tier.
- Untrusted content: chunks/tool results go into the prompt only through `context.data_block(...)` (tagged, escaped). Never concatenate retrieved text into the system prompt.
- Errors: `AppError(code, message, http_status)` → single handler → `{error:{code,message}}`.
- Config only via `core/config.py` (pydantic-settings); env names in `.env.example`.
- Tests: `pytest` + `httpx.AsyncClient`, tmp SQLite per test, `FakeProvider` fixture with canned structured outputs, poisoned-chunk fixtures for retrieval. Kernel tests must not touch the network.
- `mypy --strict` on `app/`; `ruff`; line length 100. Prompts live in `prompts/` as versioned files, loaded by `orchestrator/prompts.py`.
