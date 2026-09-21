# Codex continuation — 2026-09-20

## Ownership and baseline
The owner asked Codex to take over implementation and preserve Claude Code continuity. Work directly in this checkout; do not run Claude and Codex edits concurrently. HEAD was `eb7626a`. P0–P6 and the initial P7 implementation were already present as extensive uncommitted/untracked work. Preserve them. No commit, reset, dependency install, model pull, migration application, live learner-data change, or downloader change was performed in this takeover.

Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, path rules in `.claude/rules/`, and `docs/IMPROVEMENT-PLAN.md`. Shared progress is in `docs/HANDOFF.md`; this file describes only the Codex increment. The existing Claude skills remain intact.

## Implemented: first P7 review fixes
- `backend/app/api/listening.py`: both mutating listening endpoints reject sessions belonging to another learner. The exposure endpoint verifies that the lesson and clip exist before writing an event (404 document/session, 400 clip).
- `frontend/src/features/listening/ListeningPanel.tsx`: Stop is available before a question or grade, including error states. Stop and unmount pause audio. A delayed play resolution after unmount pauses again rather than updating the abandoned view.
- `backend/tests/test_listening.py`: invalid document/negative and out-of-range clip cases emit no exposure; cross-learner task/listened requests write neither tasks nor events.
- `frontend/src/features/listening/ListeningPanel.test.tsx`: stop before answering creates no assessment/exposure requests; audio pauses on stop/unmount and on delayed play completion; low-capacity test explicitly awaits grading.

Defect reproduction from inherited source: POST listened with a valid session but nonexistent document/index reached EventWriter without loading a lesson; Stop was inside the `graded` conditional, so a learner could not exit from the initial clip or a failed task through the listening panel.

## Verification
- Inherited baseline: `make test`: 227 backend / 30 frontend passed.
- After implementation: full `make test`: 230 backend / 31 frontend passed.
- After review additions: `uv run pytest -q tests/test_listening.py`: 10 passed; `pnpm exec vitest run src/features/listening/ListeningPanel.test.tsx`: 4 passed.
- Final `make lint`: ruff, formatter, mypy (128 files), TypeScript and ESLint passed.
- Code and pedagogy reviewers found no introduced blockers/majors in this bounded delta. Their minor test requests were addressed.
- Synthetic fixtures only; no live audio/model acceptance run. jsdom reports non-failing canvas/media implementation warnings.
- No API schema changes, so generated API types were not modified. No database migration required.

## Next: finish P7 before claiming it complete
P7 as a whole remains review-pending. Continue in this order:
1. Exposure honesty: `startTask` currently emits full nominal clip seconds even without playback and for reading fallback. Distinguish reading from audio, observed vs self-reported exposure, and avoid duplicate exposure on failed task retries. Keep exposure separate from competency evidence; update event/schema docs and tests for any contract change.
2. Provide a way past a clip whose task cannot be generated, preserving honest progress and learner control. Stop is now an exit, but it does not skip a broken clip.
3. Review answer-draft preservation on stop, stale parent `graded` state during retry, and session/block completion semantics on early exit.
4. Review concurrent task creation/idempotency, unreviewed model-item grading/evidence, provenance/citation fallback, and beginner scaffolding across the full inherited P7 flow.
5. Run complete P7 acceptance and both project reviewers; update the slice and handoff with remaining limitations. Then move to P8 (code exercise) or P9 (voice) according to the improvement plan and installed capabilities. Existing dependency/model/ADR decision boundaries still apply.

Do not mark P7 approved merely because these two scoped reviews passed. Do not commit the whole inherited tree as this small fix. Owner invokes `/commit`; use explicit file groups.
