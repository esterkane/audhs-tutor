# Slice: ci-gates (P5, 2026-09-20)

**Story.** Every push and pull request runs the same gates the owner runs locally, with locked dependencies and nothing private: no learner data, no local models, no API keys, no personal services.
**In/out.** `.github/workflows/ci.yml`, three jobs: `backend` (uv, Python 3.12, `uv sync --frozen`, `uv lock --check`, ruff check + format, mypy `app`, pytest — fake providers + SQLite retrieval repository), `frontend` (pnpm 12, Node 24, `pnpm install --frozen-lockfile`, `tsc -b`, eslint, vitest), `migrations` (empty database: `alembic upgrade head`, `downgrade -1`, `upgrade head`, `current`). `ANTHROPIC_API_KEY` and `HF_TOKEN` are set empty; the `stt` dependency group (mlx-whisper) is not installed on Linux.
**Live checks (not CI, labelled).** `make bench s=<n>` (Ollama, Qdrant, pulled models), `make evals` / `make eval-retrieval` (local model), media/STT/vision ingest with a pulled model, the owner's real experiment run, browser walk-throughs. They run on the owner's machine and are recorded in ROADMAP/slice docs as *measured*, never claimed from CI.
**Browser journeys.** Still API + component coverage: Playwright is **not** approved (see `docs/IMPROVEMENT-PLAN.md` › Dependency decisions). The workflow gains a `journeys` job the day the owner approves `@playwright/test`.
**Verified by.** The workflow mirrors `make lint` + `make test` exactly (both green locally: backend 206, frontend 28); `uv lock --check` passes locally. The workflow itself cannot be executed here (no push); first real run = first push to GitHub.

## Linux media test portability — 2026-09-21

The first public CI runs exposed eight backend test failures: SciPy was available in the developer's optional STT environment but absent from the default CI dependencies, and the registry readiness test assumed a host audio decoder. SciPy is now also a declared, locked dev dependency so WAV resampling tests run without installing the Apple-only MLX stack. Readiness tests explicitly cover absent/ffmpeg/afconvert decoders crossed with absent/present speech packages; no external decoder or model is needed for those assertions.

Validation in a clean checkout with frozen base/dev dependencies (no STT group): backend lint, formatting, mypy and lockfile check passed; full suite 293 passed before expanding the package-state matrix, followed by all 38 media tests passing with the final matrix. The tested backend matches the current committed Stage-3 curriculum plus the CI fix. Live learner data was not used. Remote validation is recorded by the GitHub Actions run for the fix commit.


### Linux browser teardown — 2026-09-24

Run 35978177388 completed all nine browser tests, then hung before the suite summary until the
25-minute job timeout. Logs show surviving make/package-manager/server descendants at cleanup.
Playwright web servers now receive SIGTERM with a five-second grace period, and the frontend runs
Vite directly under Node rather than a make → package-manager chain. This allows child shutdown
before forced cleanup and reduces inherited output-pipe owners. Local CI-mode validation passed all nine journeys in 26.2 seconds and exited cleanly. Remote
verification is pending the new GitHub run; the cancelled run is not reported as passing.
