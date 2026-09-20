# Handoff — 2026-09-19 · Stage 4 done (benchmark 5/5, experiment simulated) · next: Stage 5 `escalation-polish`

**Uncommitted:** Stage 3 *and* Stage 4 are both in the working tree (the `/commit` skill is user-invocable only). Run `/commit` — ideally twice: once for Stage 3 (ingest/retrieval/evals/guard + Udemy import + reranker), once for Stage 4.

**Done this session** (repo `~/projects/audhs-tutor`, branch `main`)
- Stage 4, all four slices (`docs/slices/{adaptation-proposals,adaptive-ux-bundle,experiments,domain-blocks}.md`):
  - `kernel/adaptation.py` — five observed-pattern rules → cards (Try / Make default / No / Don't suggest again), trials expire at the next session, undo, log; `/api/adaptations`; `AdaptationCards` on Home + Session, `AdaptationLog` under Preferences. Migration `064e2993cba7`.
  - Bundle — `planner.replan` + `/api/plan/replan` (energy check-in → planner card, `pref="session.plan"`), `/together` presence screen (opt-in brown noise), sensory prefs (`ui.theme/font_scale/notifications/ambient`) applied by `useSensory`, `models_ai/manage.py` + `/api/models` (+ background pull/bench jobs) + `/models` screen (the CLI delegates to `manage`), parking promote/drop + Home reminders, wind-down notification behind a preference.
  - `kernel/experiments.py` — templates, balanced matched-node / session assignment (logged `assigned`, arm stamped on every event and the turn meta; node-unit arm sets the questioning style per node in `TutorTurn`; session-unit arm sets `session.socratic`), outcomes from the event log (delayed recall counts only reviews ≥ 1 day after the previous review), results with 95 % CI and a literal reading; `/api/experiments`; `/experiments` dashboard; session banner. Migration `e2adb21ba4ae` (`experiment_assignment`, `session.experiment_arm_id`).
  - `kernel/practice.py` — vocabulary decks on FSRS in the LANGUAGE domain (only ever in the language block; `memory.due_items(domain=…, exclude_domains=…)`), `practiced` events, `/api/practice`, `/api/vocab`, `PracticePanel` (movement/guitar: 2–3 options, rating, skip) + `VocabPanel`, `/vocab`; the session now runs movement primers and domain-switch blocks instead of skipping them.
  - Fix found by the benchmark: `memory.review` now measures `days_since_learned` from the previous review (was wall-clock item creation → negative under time travel).

**Verified by**
- `make test`: backend 119 passed, frontend 18 passed. `make lint` green. (Occasionally a `libc++abi … recursive_mutex lock failed` line prints *after* all tests passed — an onnxruntime/thread teardown message at interpreter exit, seen in some full runs only; not a test failure. If it bothers CI, run `pytest -p no:cacheprovider` in two halves or investigate the fastembed teardown.)
- `make bench s=4`: 5/5 (numbers in ROADMAP). The two-week experiment is *simulated* with time travel; the owner's real run is the actual benchmark: create "Socratic vs explicit" under `/experiments`, Start, learn normally for two weeks, then read Results.
- Browser pane: `/models` (real registry, reranker 81.6 ms / 16 docs), `/together`, `/experiments` (empty state), Home unchanged.
- Kit reviews (second attempt; the first hit the monthly spend limit): pedagogy-reviewer "ship-with-fixes" → all 9 fixes applied; code-reviewer 3 blockers (Try without a session became permanent; trials expired *after* the next plan was built; the short-vs-long template changed nothing) + 7 majors → all applied, plus most minors. Regression tests added for each blocker/major. Backend 122 tests, frontend 18, lint green, bench 5/5 after the fixes.

**Open / owner decisions**
- Run the real experiment (above). While it runs, every explain turn on an assigned node uses that node's arm; the session screen says so.
- `gemma3:12b` still not pulled (Socratic arm on llama3.1:8b tends to explain instead of asking — the experiment will show it). `ANTHROPIC_API_KEY` still empty (`grade_rubric`, `judge` unresolved in the routing table).
- Guitar activities are a fixed list; vocab has no CSV import; `.docx/.pptx` ingest still unsupported.
- Stage 5 (`escalation-polish`, `voice-loop`, `language-voice-block`) needs the API key and the MLX voice stack (`scripts/spike_voice.py` may be run first).

**Review leftovers (deliberately not done)**
- Out-of-session events (parking promote, standalone practice, session-less cards) stamp `mode=steady, energy=3` as a sentinel — use the latest open session if you need cleaner cuts.
- `started` is emitted after the arm is assigned now, so it carries the arm; older sessions (before today) do not.
- Node-unit experiments cannot measure `completion`/`transfer` (block and evidence events are not per node) — those metrics read "not enough data" for node-unit experiments.
- `parking drop` writes no event (the verb enum is closed; add `dropped` via EVENT-SCHEMA if wanted).
- Vocab review has no confidence step (FSRS rating, not graded feedback).
- Route/kernel split: `plan.replan` and `practice.add` still do a little assembly in the router.
- Frontend tests for the energy check-in UI, `useSensory` and `SoftTimer notify` are missing; new route tests do not run axe.

**Do not**
- Assume a card was applied silently: everything the system changes is in Preferences › Adaptation log with Undo; if a preference looks changed, look there first.
- Mix domains in a block: `due_items` excludes `language` by default; pass `domain="language"` for the vocab block.
- Start two experiments of the same unit type (the API refuses).
- Run `make dev` while :8000/:5173 are taken (dev servers from today are still running).
- Hand-edit `api-types.ts`; `make gen-api` after schema changes. Exact-string edits after ruff/prettier: assert the match count.
