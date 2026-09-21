# AuDHS-Tutor

A personal, local-first learning app designed around AuDHD needs: manageable sessions, explicit choices, resumable progress and evidence-based review. Its main subjects are AI, machine learning and programming, with language, guitar and movement blocks alongside them.

**The LLM explains and reasons; the Learning Kernel remembers and decides.**

This is an actively developed, single-learner application intended for localhost. Local models handle supported tasks; hosted model routes are optional. Course material, learner data, model downloads and secrets are not included in this repository.

## What works today

- Learning sessions with block boundaries, stop/resume, confidence-before-feedback reviews and spaced repetition.
- Course material ingestion with citations, trust levels, quarantine, document versions and hybrid retrieval through Qdrant.
- Per-file and archive-member progress, outcome summaries, cancellation and resumable imports in the CLI and Corpus screen.
- Local media extraction with guarded WAV normalization, transcript caching and a bounded, versioned vision cache.
- Python exercises with a CodeMirror editor, textarea fallback and a pinned, locally served Pyodide runtime.
- A model registry with inspectable task routing, usage accounting and budget limits.
- Optional local voice using MLX Whisper and a persistent Kokoro server, including early speech at the first suitable clause.
- Learner backups, optional authenticated password encryption and explicit private full-corpus recovery.

Imported material is not automatically a reviewed or published course. Course curation and curriculum improvements remain in progress. Voice implementation is available, but the personal-recording acceptance gate remains open. See [the roadmap](docs/ROADMAP.md) and [handoff](docs/HANDOFF.md) for current evidence and outstanding work.

## Local setup

The primary development target is **macOS on Apple Silicon**. The optional MLX speech stack requires that platform. CI tests the core application on Linux using fake model providers.

Prerequisites:

- Homebrew and `jq` for the bootstrap script.
- A running Docker-compatible engine, such as Docker Desktop or OrbStack, for Qdrant.
- Node.js 24; CI uses pnpm 12. Python 3.12 is the tested backend version, managed through `uv`.

From a terminal:

```bash
git clone https://github.com/esterkane/audhs-tutor.git
cd audhs-tutor
./scripts/bootstrap.sh
```

The script installs missing CLI tools through Homebrew, installs backend/frontend dependencies, creates `.env` if absent, starts Qdrant and attempts to pull `llama3.1:8b`, `gemma3:12b` and `nomic-embed-text`. Model downloads require network access and disk space. Use `./scripts/bootstrap.sh --no-models` to skip those model pulls.

Review `.env` before starting. For local-only use, leave `ANTHROPIC_API_KEY` empty and set `DAILY_BUDGET_USD=0`; tasks that require an unavailable hosted model will remain unavailable. Ollama must be running for local inference and embeddings.

```bash
# Install and verify the browser Python runtime on each machine serving the app.
make pyodide
make pyodide-verify

# Register the configured models and inspect readiness.
make models args=seed
make models args=list

# Start Qdrant, the API and the frontend.
make dev
```

Open **http://localhost:5173**. The API runs on port **8000**, with API documentation at **http://localhost:8000/docs**; Qdrant uses port **6333**. The API applies database migrations at startup. The bootstrap script's historical `/build-stage 0` message is not a required setup step: the application is already implemented.

For a disposable walkthrough, run `make dev-sandbox` and open **http://localhost:5174**. It recreates and seeds `data/sandbox.db` on each start, uses API port 8010 and disables hosted models. It does not use the learner's `data/dev.db`.

## Import course material

Use an absolute source path because the Makefile runs the importer from `backend/`:

```bash
make ingest src="/absolute/path/to/course" course="My course"
make ingest-runs

# After a graceful stop (Ctrl-C), resume the interrupted run.
make ingest src="/absolute/path/to/course" resume=1

# Inspect supported formats and local model readiness.
uv run --project backend python scripts/ingest.py --capabilities
```

The importer handles documents, slides, captions, notebooks, source code and supported archives. Audio/video and images depend on available decoders and ready speech/vision models. Qdrant and the embedding model must be available for indexing. Imported code is treated as source material, not executed.

Progress and outcome classes distinguish imported/unchanged files, reference links, empty content, unsupported formats, unavailable capabilities, access restrictions and errors. Resume retains the original run settings and skips completed paths; use a normal new run to detect changed files. Progress is not reported within an individual long media conversion, and a hard-killed process may leave a run marked `running`.

The CLI defaults to trust level 2 for purchased course material. For public or community material, set the trust explicitly:

```bash
uv run --project backend python scripts/ingest.py \
  --src "/absolute/path/to/public-material" --course "Public material" --trust 1
```

This repository imports files you already have. The separate Udemy resource downloader is not bundled here, and ingestion does not download an entire Udemy library or publish curricula automatically.

## Optional voice and media models

Install the backend speech dependencies, including the declared `scipy` resampler:

```bash
uv sync --project backend --group stt
make models args="pull whisper-large-v3-turbo"
make models args="pull silero-vad"
```

When running Makefile targets after installing the optional group, `UV_NO_SYNC=1 make dev` (and similarly `make ingest`) preserves the prepared environment; resync it explicitly when dependencies change. Installing a standalone `mlx-whisper` tool does not install the backend's optional dependency group.

Voice output needs a separately running, OpenAI-compatible Kokoro server configured with `KOKORO_URL` (default `http://localhost:8880`). `make dev` does not start Kokoro. Use **Models → Voice → verify** to check the services before explicitly enabling voice; microphone capture is not enabled automatically. Silero is optional, with the energy-based VAD fallback reported in readiness.

Relevant `.env` settings:

```dotenv
TRANSCRIPT_CACHE_DIR=./data/transcripts
VISION_CACHE_DIR=./data/vision
STT_LANGUAGE=
VOICE_DIR=./data/voice
KOKORO_URL=http://localhost:8880
```

Blank `STT_LANGUAGE` enables automatic language detection. Speech recognition and synthesis have separate language capabilities; German output is unavailable with the currently adopted Kokoro v1 stack. Public-corpus benchmark results are evidence, not a substitute for the personal-recording gate. See [the voice decision](docs/adr/0011-local-voice-runtime.md) and [voice slice](docs/slices/voice-loop.md).

## Backups and database changes

```bash
# Prompts for a password; defaults to learner-only scope.
make backup out="/absolute/path/to/backup.zip.enc" encrypt=1
make backup-inspect f="/absolute/path/to/backup.zip.enc"

# Check migrations against a disposable database copy before applying them.
make migrate-check
make migrate-apply
```

Without `encrypt=1`, backups are unencrypted. `scope=full` includes corpus text and is intended for private recovery. Secrets, original course files, downloaded models and Qdrant vectors are not bundled in backups. Restore targets must be empty; follow [the recovery guide](docs/RECOVERY.md).

## Development and checks

```bash
make lint
make test

# One-time browser installation, then sandbox browser journeys.
(cd frontend && pnpm exec playwright install chromium)
make pyodide
make test-e2e
```

CI runs backend lint/type checks/tests, frontend checks/tests, database migration checks and Playwright journeys. Local model benchmarks and personal voice acceptance are separate from CI. Check [GitHub Actions](https://github.com/esterkane/audhs-tutor/actions) for actual run results.

| Area | Implementation |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, SQLite/WAL and Alembic |
| Frontend | React, TypeScript, Vite, TanStack Query and Zustand |
| Retrieval | Qdrant dense/sparse search with source provenance |
| Models | Ollama, optional hosted routes, MLX Whisper and Kokoro |
| Exercises | CodeMirror and local Pyodide |

Start with [architecture](docs/ARCHITECTURE.md), [ADRs](docs/adr/), [improvement plan](docs/IMPROVEMENT-PLAN.md) and [handoff](docs/HANDOFF.md). Coding agents should read [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md); shared procedures, reviews and hooks live in `.claude/`. Keep `.env`, `data/`, downloaded Pyodide files and private prompt packages out of commits.
