# Handoff — 2026-09-19 · Stage 1 built · next: model decision, then Stage 2

**Done this session** (repo `~/projects/audhs-tutor`, branch `main`)
- Stage 1, all six slices: `seed-attention` (8 skills, 20 assessments, 14 chunks in `corpus_v1`), `context-packet`, `tutor-turn` (SSE), `assess-evidence` (hierarchical grader), `fsrs-memory`, `session-screen` (Home → Session → Review → Recap, parking lot, soft timer). Specs in `docs/slices/*.md`.
- Kernel: `kernel/{skill_graph,competency,memory,session,seed,learner}.py`; orchestrator: `orchestrator/{prompts,context,actions,tools,tutor,grader}.py`; API: `api/{learner,skills,sessions,tutor,assess,review,parking}.py`; evals: `app/evals/{hardchecks,harness}.py`, `scripts/run_evals.py`, `evals/cases/*.yaml`; `scripts/bench_stage1.py`.
- Pedagogy review (kit agent) applied: strict full-solution gate, scaffold-by-mastery, truthful `[n]` citations, real hint counts, review confidence before reveal, logged + undoable review cap, "Which first?" instead of auto-routing, retrieval-first next steps, calibration wording.
- Verified in the real UI (browser pane): explain streamed with `[1]` citation and sources → MCQ graded, mastery 21%, next review scheduled → recap saved.

**Verified by**
- `make test`: backend 49 passed, frontend 7 passed. `make lint` green (ruff, mypy --strict, tsc -b, eslint incl. react-hooks purity).
- `make bench s=1`: A/B/C/E PASS, D FAIL (2/5 hard checks; numbers in ROADMAP Stage 1).
- `scripts/run_evals.py`: results in `evals/results/latest.json` (no baseline committed yet — commit one after the model decision).

**Open / blocked**
- Model decision (owner): `explain_simple`/`hint` route to `gemma3-12b` first (not pulled) and fall back to `llama31-8b`, which ignores sentence limits and Socratic mode. Options: `make models args="pull gemma3-12b"` then `make models args="bench gemma3-12b"`, and/or set `ANTHROPIC_API_KEY` + `make models args=seed` so hosted models become ready. Then `make bench s=1` and commit `evals/results/baseline.json`.
- React 19 (Vite scaffold) vs "React 18" in CLAUDE.md binding decisions — working fine; record via `/adr` or downgrade.
- ADR-0001 keeps LiteLLM behind `ClaudeProvider`; the claude-api skill recommends the official SDK. Revisit in Stage 5 (caching/thinking control).
- Not yet: Playwright smoke tests, axe run, sensory settings screen, adaptation log UI (Stage 4), movement/language blocks.

**Next step**
Owner decides the model (above) → rerun `make bench s=1` → `/build-stage 2` (`skill-map` first; the open learner model data already exists at `GET /api/skills`).

**Do not**
- Run `make dev` while another process holds :8000 — two stale servers from `~/projects/agentic-job-scout` were on that port today and were killed; check `lsof -nP -iTCP:8000` first.
- Use `git add -A -- ':!data'` (pathspec fails); plain `git add -A` is safe.
- Hand-edit `frontend/src/lib/api-types.ts`; run `make gen-api` after any API schema change.
- Expect `pnpm exec …` to work from `backend/`; the Claude Code shell resets cwd between calls — use absolute `cd`.
- Edit multi-line code with exact-string replacements after `ruff format`/`prettier` ran; match on a unique line instead.
