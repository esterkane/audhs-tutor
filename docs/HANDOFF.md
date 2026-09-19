# Handoff — 2026-09-19 · Stage 2 done (benchmark 4/4) · next: Stage 3 `ingest-pipeline`

**Done this session** (repo `~/projects/audhs-tutor`, branch `main`)
- Stage 2, all five slices: `preferences-checkpoints`, `planner-v1`, `skill-map`, `representations`, `challenge-modes` (`docs/slices/*.md`). Kernel: `kernel/{preferences,planner,representations}.py`, `skill_graph.map_view`; orchestrator: `orchestrator/{representations,challenge}.py`; API: `/preferences`, `/plan`, `/skills/map`, `/objects/{skill}/representations`, `/challenge`, `/sessions/current` + `/checkpoint`; UI: Map, Preferences, plan strip + block flow, cached "show it differently" with preference pairs, challenge panel, resume.
- Stage 1, all six slices: `seed-attention` (8 skills, 20 assessments, 14 chunks in `corpus_v1`), `context-packet`, `tutor-turn` (SSE), `assess-evidence` (hierarchical grader), `fsrs-memory`, `session-screen` (Home → Session → Review → Recap, parking lot, soft timer). Specs in `docs/slices/*.md`.
- Kernel: `kernel/{skill_graph,competency,memory,session,seed,learner}.py`; orchestrator: `orchestrator/{prompts,context,actions,tools,tutor,grader}.py`; API: `api/{learner,skills,sessions,tutor,assess,review,parking}.py`; evals: `app/evals/{hardchecks,harness}.py`, `scripts/run_evals.py`, `evals/cases/*.yaml`; `scripts/bench_stage1.py`.
- Code review (kit agent) applied: output-contract sections were being dropped by the token budget (root cause of the earlier eval failures), gateway events/abort-safe traces, error mapping, review time-travel hardening, seed cycle check, 8 regression tests.
- Pedagogy review (kit agent) applied: strict full-solution gate, scaffold-by-mastery, truthful `[n]` citations, real hint counts, review confidence before reveal, logged + undoable review cap, "Which first?" instead of auto-routing, retrieval-first next steps, calibration wording.
- Verified in the real UI (browser pane): explain streamed with `[1]` citation and sources → MCQ graded, mastery 21%, next review scheduled → recap saved.

**Verified by**
- `make test`: backend 65 passed, frontend 10 passed. `make lint` green (ruff, mypy --strict, tsc -b, eslint incl. react-hooks purity).
- `make bench s=1`: 5/5 PASS (hard checks 4/5 = 0.8); `make bench s=2`: 4/4 PASS; numbers in ROADMAP; `evals/results/baseline.json` committed.
- `scripts/run_evals.py`: results in `evals/results/latest.json`, baseline in `evals/results/baseline.json`.

**Open / blocked**
- Socratic mode: llama3.1:8b explains instead of asking (1/5 eval cases). Pull the plan's default (`make models args="pull gemma3-12b"`, then `bench`) or set `ANTHROPIC_API_KEY` + `make models args=seed`; rerun `make bench s=1` and compare against `evals/results/baseline.json`.
- React 19 (Vite scaffold) vs "React 18" in CLAUDE.md binding decisions — working fine; record via `/adr` or downgrade.
- ADR-0001 keeps LiteLLM behind `ClaudeProvider`; the claude-api skill recommends the official SDK. Revisit in Stage 5 (caching/thinking control).
- Not yet: Playwright smoke tests, axe run, sensory settings beyond the preference registry, adaptation proposal cards / undo UI (Stage 4), movement/language/domain-switch blocks (planner emits them as optional/skip; no screens yet), n-of-1 experiments.
- The 8B grader scored a challenge answer 0 while its feedback text said the learner "correctly identifies the issue": grader consistency is model-limited; hosted `grade_rubric` would take over once an API key exists.

**Next step**
`/build-stage 3` — `ingest-pipeline` first (Udemy captions/slides/notebooks/PDFs → `knowledge/ingest/`; the markdown path, provenance, versioning and `reindex` already exist), then `hybrid-retrieval` polish (reranker, `retrieval_trace` is already written), `retrieval-evals`, `untrusted-content-guard` (data-block escaping + `fake_section` flag exist; add poisoned-chunk end-to-end tests through `TutorTurn`). Optional before that: pull `gemma3:12b` for Socratic sessions.

**Do not**
- Run `make dev` while another process holds :8000 — two stale servers from `~/projects/agentic-job-scout` were on that port today and were killed; check `lsof -nP -iTCP:8000` first.
- Use `git add -A -- ':!data'` (pathspec fails); plain `git add -A` is safe.
- Hand-edit `frontend/src/lib/api-types.ts`; run `make gen-api` after any API schema change.
- Expect `pnpm exec …` to work from `backend/`; the Claude Code shell resets cwd between calls — use absolute `cd`.
- Edit multi-line code with exact-string replacements after `ruff format`/`prettier` ran; anchor on a unique line, assert the match count, and grep afterwards — several edits silently no-op'd today until asserted.
- Dev servers started today are still running (uvicorn --reload on :8000 via nohup, vite on :5173 via `make dev`); stop them with `lsof -nP -iTCP:8000,5173` + `kill` if they get in the way.
