# Handoff — 2026-09-19

Repo created from the starter kit (plan v2.2) at `~/projects/audhs-tutor`, git initialised on `main`.
Stage 0 slice `repo-bootstrap` is done and verified on this Mac (M4 Pro, Docker Desktop):
- `./scripts/bootstrap.sh --no-models` ran clean (made idempotent for non-brew tools; `uv init --bare`; non-interactive create-vite).
- `backend/`: uv project, flat `app/` package (no src layout), `app/core/config.py` Settings, `app/main.py` with `GET /api/health`, ruff/mypy/pytest configured, 1 smoke test.
- `frontend/`: Vite 8 + React 19 + TS, ESLint, Prettier, Vitest (jsdom) with 1 smoke test, kit deps added.
- Qdrant running via `docker compose` (`:6333`, empty). Ollama on `:11434` has `mxbai-embed-large` only — `nomic-embed-text`, `llama3.1:8b`, `gemma3:12b` not pulled yet (bootstrap was run with `--no-models`).
- `make test` and `make lint` are green. `.env` and `.claude/settings.local.json` exist locally (gitignored, untouched defaults; `ANTHROPIC_API_KEY` empty).

Next step: in Claude Code inside this repo run `/build-stage 0` — remaining slices `db-core`, `model-provider`, `model-registry`, `qdrant-repo`, `events-traces`, then `bench_stage0.py`.
Before `model-provider`: pull models (`ollama pull llama3.1:8b nomic-embed-text` or via `scripts/models.py`) and set `ANTHROPIC_API_KEY` in `.env`.
Do not: reintroduce a LiteLLM proxy, LangGraph or multi-agent tutoring in Phase 1. Qdrant is the retrieval store from day one (ADR-0002); models go through the registry (ADR-0010), never hardcoded.
