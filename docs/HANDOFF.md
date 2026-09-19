# Handoff — 2026-09-19 · Stage 0 done · next: Stage 1 (`seed-attention`)

**Done this session** (repo `~/projects/audhs-tutor`, branch `main`, 7 commits)
- `repo-bootstrap`, `db-core`, `events-traces`, `model-provider`, `model-registry`, `qdrant-repo` — all Stage 0 slices; specs in `docs/slices/*.md`.
- `backend/app/db/models.py` (32 tables, Alembic `08e0e269a737`, append-only `learning_event` triggers), `db/events.py` + `db/traces.py`, `models_ai/{provider,ollama,claude,fake,routing,budget,registry,gateway,downloader,bench,factory}.py`, `knowledge/{repository,provenance,qdrant_hybrid,sqlite_hybrid}.py`, `scripts/{models,reindex,export,wipe,bench_stage0}.py`.
- Registry seeded (`make models args=seed`): llama31-8b, nomic-embed-text ready; gemma3-12b, qwen3-coder-30b-a3b, hosted-strong (Claude Sonnet 5), hosted-medium (Claude Haiku 4.5) available; qwen25-05b-q4 pulled from HF and benchmarked. `routing.chat` = llama31-8b (benchmarked 47.5 tok/s).

**Verified by**
- `make test` → backend 31 passed (incl. Qdrant integration test), frontend 1 passed. `make lint` green (ruff, mypy --strict, tsc, eslint).
- `make bench s=0` → PASS 4/5, B skipped (numbers in ROADMAP Stage 0; raw `evals/results/bench_stage0.json`).

**Open / blocked**
- `ANTHROPIC_API_KEY` empty → check B (real Claude `grade_rubric` with cost) not run; ClaudeProvider is exercised only via FakeProvider. Set the key in `.env`, run `make models args=seed` (marks hosted rows ready) then `make bench s=0`.
- ADR-0001 says LiteLLM SDK behind `ClaudeProvider`; the Claude API skill recommends the official `anthropic` SDK (adaptive thinking, `messages.parse`, exact cache accounting). Kept LiteLLM per ADR; revisit with `/adr` if caching/thinking control is needed in Stage 5.
- gemma3-12b / qwen3-coder not pulled (`make models args="pull gemma3-12b"`); until then hint/explain routes fall back to llama31-8b (logged as `route=fallback`).
- `.claude/settings.json` deny-lists `Read(./data/**)` and hooks block editing `data/`; the benchmark writes Qdrant collection `corpus_v900` and deletes it — production collection is `corpus_v1` (empty until Stage 3 ingest).

**Next step**
`/build-stage 1` → first slice `seed-attention` (6–10 `skill_node`s + `learning_object`s for attention; hand-ingested chunks into `document`/`chunk`/`chunk_provenance`, then `scripts/reindex.py`). Then `context-packet`, `tutor-turn` (uses `ModelGateway.complete(TaskClass.EXPLAIN_SIMPLE…)` + `write_tutor_trace` + `EventWriter`).

**Do not**
- Hand-write migrations; use `make migrate m="…"` (env.py reads the URL from Settings; tests assert migration == ORM).
- Put model names outside `routing_profiles.yaml`/registry. HF GGUF models are addressed in Ollama by their registry id.
- Use `git add -A -- ':!data'` (pathspec magic fails on this git); plain `git add -A` is safe, `.gitignore` covers `.env`/`data/`.
- Run `sleep` in Claude Code Bash foreground; use background tasks/Monitor.
