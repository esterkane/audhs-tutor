# AuDHS-Tutor — project memory for Claude Code

Personal, local-first, AuDHD-centred **learning operating system with AI capabilities** (not a chatbot with flashcards). One learner (the owner, "Saru").
Subjects: AI / LLMs / ML / DL / programming (primary); language + guitar + movement blocks (interleaved).
Runs on a MacBook Pro M4 Pro, 48 GB. Phase 1 = localhost only, one container (Qdrant), low cost, hybrid LLM routing.

Read `docs/ARCHITECTURE.md` before touching structure. Every non-trivial choice is an ADR in `docs/adr/`.
Detailed rules load per path from `.claude/rules/`. Procedures are skills (`/build-stage`, `/feature-slice`, …). The improvement programme P0–P9 lives in `docs/IMPROVEMENT-PLAN.md`. `/commit`, `/build-stage`, `/handoff`, `/adr` are invoked by the owner only.

## Core principle
**The LLM explains and reasons. The Learning Kernel remembers and decides.** The LLM never owns learner state, curriculum state, competency, memory or truth. Retrieval supplies evidence; assessments produce competency evidence; FSRS manages memory; the learner controls adaptation; observability tells us whether any of it works.

## Owner continuation instruction — 2026-09-24

Local execution whenever accurate and capable; OpenAI only for demonstrated local gaps. Key setup
must not silently switch task assignments. Current OpenAI slice, tests and evidence are in
`docs/slices/openai-provider.md`; full Claude tooling audit in `docs/CLAUDE-CONFIG-AUDIT.md`.
The extension uses the existing ModelProvider/gateway boundary; existing accepted ADRs remain intact.

## Binding decisions (change only via /adr)
- Layers: `Learning UX → Learning Kernel (deterministic) → Tutor Orchestrator (one, tool-using) → Knowledge + Models → Persistent state → Evaluation/Observability/Security`. ADR-0007.
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLite (WAL) via SQLAlchemy 2 + Alembic, `uv`. Plain Python + Instructor for structured output; PydanticAI only when a typed tool loop is needed. No LangGraph, no multi-agent tutor in Phase 1.
- Frontend: TypeScript, React 19, Vite, TanStack Query, Zustand (`stores/mode.ts` = `useMode`), shadcn/ui + Radix, CodeMirror 6, Pyodide. `pnpm`. (Was written as React 18; package.json has had React 19 since Stage 0 — reconciled 2026-09-20, no design change.)
- Models: `ModelProvider` interface (`OllamaProvider`, `ClaudeProvider`, `OpenAIProvider`; MLX Whisper handles registry-routed `TaskClass.STT`; Kokoro serves `TaskClass.TTS` via its local HTTP service (ADR-0011)) with LiteLLM **SDK** behind it. A **model registry** (`model_registry` table, `scripts/models.py`, Settings › Models) lets the learner download models from Hugging Face / Ollama library / mlx-community, benchmark them, and assign one per `TaskClass`; routing stays inspectable and logged. No proxy in Phase 1. Budget cap enforced in-app. ADR-0001, ADR-0010, ADR-0014.
- Retrieval: `RetrievalRepository` interface; production adapter from day one is **Qdrant** (dense + sparse named vectors, server-side fusion, payload filters, provenance, quantization). Raw chunks stay in SQLite; `reindex.py` rebuilds Qdrant. `SqliteHybridRepository` (FTS5 + sqlite-vec) only for tests/offline fallback. ADR-0002.
- Learner model: `MemoryState` (FSRS via `py-fsrs`, per item) **≠** `CompetencyState` (per skill, derived from `competency_evidence`). Mastery is a computed view over both. Skill graph with prerequisite edges is the curriculum backbone. ADR-0004.
- Content: `LearningObject` (concept, goal, sources, examples, exercises, success criteria) rendered into `Representation`s (map, simple/deep explanation, analogy, worked example, diagram, audio, quiz, code exercise, explain-back). "Show it differently" changes the representation, never the source of truth.
- Grading: deterministic → rubric checks → local LLM → hosted model; LLM grades return per-criterion evidence, never bare scores. ADR-0009.
- Security: retrieved documents and tool results are **untrusted data**, structurally separated from system policy and app state. Model-generated code runs only in Pyodide or a resource-limited sandbox. ADR-0008.
- Context: every tutor turn gets a bounded `ContextPacket` (policy, preferences, session state, learning contract, evidence, retrieved knowledge, request, output contract). Never the full chat history. Three stores: raw event log (audit) / session checkpoint (temporary) / structured learner state (durable).
- Observability from day one, in SQLite: `tutor_trace`, `retrieval_trace`, `model_call` + the learning-event log (`docs/EVENT-SCHEMA.md`). Langfuse optional later.
- Voice (Phase 4): Silero VAD → whisper large-v3-turbo (MLX) → streaming LLM → Kokoro-82M persistent server. MLX Whisper for STT; Kokoro server for TTS on localhost; Ollama for general inference. [ADR-0011](docs/adr/0011-local-voice-runtime.md).
- Multi-user readiness: `learner_id` on every learner-scoped table from day one; ULIDs; no module-level singletons; repositories behind interfaces.

- Private recovery: learner-only default; full corpus only for explicit private recovery; cryptography approved, encryption implementation pending. [ADR-0012](docs/adr/0012-private-backup-policy.md).
- Browser/editor dependencies approved: Playwright and CodeMirror Python/commands. Pinned local Pyodide is the target; current CDN remains until implemented. Defer pypdfium2. [ADR-0013](docs/adr/0013-browser-editor-and-pdf-dependencies.md).

## Pedagogy guardrails (every tutor prompt and grader)
- Hint-first, one step at a time, brief. Full solution only on explicit request, then a check question.
- Explicit-explanation default; Socratic questioning opt-in per session. Never silently switch.
- Direct, literal, unambiguous. Concrete options, not open feeling-questions.
- Cite provenance for corpus claims; say "no source" otherwise.
- Confidence rating before feedback on assessed items.
- No "learning styles" typing; multiple representations instead.
- Optimize for delayed retention and competency evidence, not satisfaction. Gamification off by default; no streaks.
- Ask the learner only for private/preference-dependent information; solve knowledge gaps with retrieval.

## AuDHD UX invariants
- Learner-selectable state modes (Novelty / Steady / Low-capacity) + energy. Adaptations are *proposed* (Try / Make default / No / Don't suggest again), logged, reversible. No "AuDHD ⇒ always X" assumptions.
- Single-task screens; parking lot always reachable; minimum-viable session/review everywhere; soft timers only.
- Domain switches only at block boundaries. WCAG 2.2 AA; reduced motion; no autoplay.

## Working conventions
- Vertical slices: schema → kernel/service → API → UI → tests → traces/events → docs (`/feature-slice`).
- Tests required for kernel, services, routes (`pytest`, `vitest`). Run before declaring done.
- Never commit secrets; config only via `backend/app/core/config.py`.
- Prefer executable scripts/notebooks over manual command sequences (owner preference). One-off tooling in `scripts/`.
- Conventional Commits via `/commit`. Unsure about a product/pedagogy decision → read `docs/adr/`, then ask.

## Commands
`make dev` (backend :8000 + frontend :5173 + Qdrant :6333) · `make dev-sandbox` (fresh seeded `data/sandbox.db`, backend :8010 + frontend :5174, hosted budget 0 — walk-throughs never touch `data/dev.db`) · `make pyodide` (pinned local Python runtime for the code exercise) · `make models` (registry CLI) · `make test` · `make lint` · `make migrate m="msg"` (generate) · `make migrate-check` (disposable DB) · `make migrate-apply` · `make ingest src=<path>` · `make evals` · `make bench s=<stage>`


Owner decision (2026-09-24): confidence ratings are optional and collapsed by default. Never block feedback, revealing a review answer, stopping, or changing topic on confidence or a grasp check. Omitted confidence stays null; clear/later labels are self-report, not mastery evidence. This supersedes mandatory-confidence guidance above.
