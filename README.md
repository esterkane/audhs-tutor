# AuDHS-Tutor

A personal, local-first learning app designed around AuDHD needs: manageable sessions, explicit choices, resumable progress and evidence-based review. Its main subjects are AI, machine learning and programming, with language, guitar and movement blocks alongside them.

**The LLM explains and reasons; the Learning Kernel remembers and decides.**

This is an actively developed, single-learner application intended for localhost. Local models handle supported tasks; hosted model routes are optional. Course material, learner data, model downloads and secrets are not included in this repository.

## Why this app exists

The aim is to help the learner direct their own learning while reducing the work of organizing it. Courses, notes and conversations can supply explanations; the app connects them to a goal, practice, feedback and a reliable place to resume.

The intended learning loop is:

**Choose a meaningful goal → explore relevant material → explain and practise → get feedback → return later → apply the idea in a new situation.**

Watching a lesson, remembering a definition, explaining an idea and solving a new problem are different achievements. The app keeps review scheduling separate from evidence of competence, and makes that evidence inspectable. Its success should be judged by what the learner can do independently and how easily they can return to learning.

### Freedom of choice with useful defaults

The learner owns the goal. The app recommends a next step and explains why, while keeping alternatives accessible. Resume, a short review or learning toward a goal should be enough to get started; choosing every setting should not become a prerequisite for learning.

Adaptations are proposed explicitly, with options to try them for a session, adopt them, decline or stop future suggestions. Accepted changes are reversible. Explicit explanation is the default; Socratic questioning and challenge blocks are opt-in. Hints support practice, and a full solution remains available on explicit request.

These are design commitments to learner agency, not assumptions that everyone with AuDHD needs the same experience. The intended experience allows stopping without punishment and changing direction without losing one's place.

### Switching with a purpose

Different switches serve different needs:

| Change | Purpose |
| --- | --- |
| Explanation → diagram → code | Explore the same concept from another angle |
| One problem type → a related problem type | Practise deciding which method applies |
| AI → language or guitar | Change activity at a clear block boundary |
| Learning → pause or movement | Make room for capacity and recovery |

The planner protects continuity by scheduling domain changes at block boundaries. Checkpoints and a tangent parking lot make returning easier. Cross-domain switching is an option for engagement and session structure; this project does not claim that switching subjects automatically improves retention. A suggested consolidation check should help the learner leave a useful checkpoint, never become a barrier to stopping.

### Critical thinking includes questioning the tutor

The tutor, its sources and its generated answer keys can be wrong. Citations and confident wording do not establish that a claim is true.

Opt-in challenges include finding a planted error, constructing a strong alternative argument (steelman), explaining an idea back and comparing confidence with performance. The broader aim is to practise asking: What supports this claim? Which assumptions does it need? Where does this analogy fail? What evidence would change my conclusion?

Feedback should explain its criteria and supporting evidence. Supporting defensible alternative answers and making grades contestable are continuing evaluation requirements; model-generated grading is not an unquestionable authority.

### Different approaches, shared learning objectives

“Show it differently” changes the representation of an idea while preserving its objective and source content. A short explanation, worked example, derivation, analogy or code exercise can expose different aspects of the same concept. These are tools to choose for the task, not fixed “learning style” labels assigned to a person.

Preference and learning outcomes are tracked separately: an explanation can feel helpful without establishing later recall or transfer. The project therefore includes delayed reviews and personal experiments, with uncertainty made visible when evidence is sparse.

### What remains to be demonstrated

The local research notes inform the design, but are incomplete and do not establish the effectiveness of this application. Some thresholds, timing rules and adaptation policies remain provisional choices to evaluate in real use. Automated tests verify software behavior; they do not demonstrate improved learning.

The next meaningful product test is one curated course followed through a complete learning loop: start easily, understand something difficult, stop safely, resume with context and later solve a new problem independently. More imported files or more AI features alone do not establish that outcome.

The rationale is recorded in the decisions on [tutoring modes](docs/adr/0003-tutoring-mode-policy.md), [memory and competence](docs/adr/0004-learner-model-n1.md), [switching and interleaving](docs/adr/0006-interleaving-and-blocks.md), and the [personal experiment analysis](docs/slices/experiment-analysis-v2.md).

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

Review `.env` before starting. For local-only use, leave both `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` empty and set `DAILY_BUDGET_USD=0`; tasks that require an unavailable hosted model will remain unavailable. Ollama must be running for local inference and embeddings.

Optional OpenAI setup: add `OPENAI_API_KEY=your_key` to the local `.env`, then restart the backend.
The Models screen lists **GPT-6 Luna** as an evaluation candidate; adding a key does not change
routing. Hosted benchmarks are paid and use the shared daily cap. Keep accurate tasks local;
use hosted inference only for a demonstrated local capability/accuracy gap, with task-specific
evaluation before assignment. The six-request synthetic compatibility check passed, including a
code explanation that the local model missed; this is not a general tutoring/grading quality gate.
See [provider evaluation](docs/slices/openai-provider.md) and [cost comparison](docs/PROVIDER-COST-COMPARISON.md).


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

The importer handles documents, slides, captions, notebooks, source code and supported archives. Audio/video and images depend on available decoders and ready speech/vision models. Qdrant and the embedding model must be available for indexing. Imported code is treated as source material, not executed. n8n workflow JSON exports are searchable by node types, connections and teaching notes, including inside supported archives. Credential fields, parameter values and runtime data are omitted; keep the original file for configuration.

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

### Coding playground

Open **Playground** for saved Python experiments with a tutor alongside the editor. Start freely or follow a worked example → complete a transformation → build a new transformation. Code runs in the existing browser Python runtime; practice checks do not update mastery. Code, predictions and recent chat stay in this browser. Tutor requests share the current workspace and bounded recent chat through the configured model route; a learning session is required for tutor activity logging. AI guidance is fallible—verify explanations against actual output.

The big-picture panel shows a conceptual input → transform → output pipeline. Visual workflow editing and real LangChain/n8n execution are later stages, not included in this version. See [playground scope](docs/slices/playground.md) and the [hosted-provider cost comparison](docs/PROVIDER-COST-COMPARISON.md).
