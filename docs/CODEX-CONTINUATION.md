# Latest: session clarity and topic isolation — 2026-09-24

Owner reported repeated confidence demands, questions without help, unclear exits and dot-product questions for every area. ADR-0016 and docs/slices/session-clarity.md implement the new flow.

- Goal selection is strict: no active lesson means a clear review/activation link. Area links preselect the right area. Starting snapshots one selection for lesson plan and review scope; old sessions explicitly show their own topic.
- Confidence is optional/collapsed for assessments, challenges, code, listening and review. Omission remains null. Recap ratings are optional. Stop session and Change topic finish without a question or recap; soft-timer stop uses the same path. Stopping before an explanation creates no unseen recall item.
- Lesson context, inline question hints/explanations and opt-in local read-aloud are available. Draft answers and delivered assistance survive explanation navigation; storage failures cannot hide a successful grade. Review assistance is logged and caps FSRS ratings at Hard.
- Clear/Ask me later labels persist as explicit bookmarks, never mastery evidence. Home lists saved lessons with Revisit. No new database migration/dependency, no live draft activation or learner-history rewrite.
- pedagogy.v2 versions the optional-confidence prompt; v1 stays unchanged. Required code/pedagogy reviews rechecked and cleared all major findings.

Verification: 374 backend tests, 63 component tests, 10 isolated Playwright journeys, generated API types and lint passed. Browser screenshot inspected. Required code and pedagogy re-reviews report no remaining majors. Tests use fakes/disposable data; the local 3/5 tutor comparison remains a separate incomplete quality gate.

Quality evidence: local Gemma broad tutor suite remained 3/5 hard checks with both old and final prompts (different brevity failures); the broader quality gate stays open. This UI change does not certify generated explanations/hints as always correct or answer-withholding. No paid API was used. Personal voice benchmark gate remains unchanged.

# Active continuation — 2026-09-24

Latest implementation: editable cross-course learning areas and explicit question feedback (ADR-0015).
Read the newest `docs/HANDOFF.md` section first; earlier entries below are historical.
All Claude project skills/settings/hooks/MCP definitions were audited; see `docs/CLAUDE-CONFIG-AUDIT.md`.
Owner policy: accurate local execution first, OpenAI only for demonstrated gaps. Provider integration
and synthetic compatibility evidence do not authorize a blanket tutoring/grading route switch.
Do not run Claude and Codex edits concurrently. Preserve personal configuration and private data.

## Current update — 2026-09-21: accepted decisions and local TTS

Owner accepted ADR-0011–0013 ("Paket annehmen"); statuses are now Accepted. Earlier pending-decision notes below are historical.

Kokoro is running in Docker as `audhs-kokoro`, bound only to `127.0.0.1:8880`, with restart policy `unless-stopped`. Image: `ghcr.io/remsky/kokoro-fastapi-cpu@sha256:ee3111d6a2c903ed62f3b4fa19543c6901205ed39fce3c177e895b34a8386b9c` (arm64). Local `.env` has `KOKORO_URL=http://127.0.0.1:8880`; restart the backend to reload settings. Stop/start: `docker stop audhs-kokoro` / `docker start audhs-kokoro`. Docker Desktop must be running.

Verified: GET `/v1/audio/voices` returned 72 voices; POST `/v1/audio/speech` with synthetic English text returned 101232 bytes PCM. No microphone capture or voice activation was performed. This is a service smoke test, not the Stage-5 latency/recognition benchmark; that gate remains open. Kokoro v1 does not provide German TTS.

Next implementation order (recommended):
1. Playwright journeys against isolated sandbox data: session boundaries/reload, review confidence, stop/resume; no paid providers.
2. CodeMirror Python editor: preserve drafts, keyboard escape, textarea fallback; browser regression coverage.
3. Encrypted backups: authenticated versioned format with bounded resource use, wrong-password/tampering/round-trip tests; retain learner default and explicit private full scope. Current ZIPs remain unencrypted.
4. Pinned locally served Pyodide plus NumPy/lock metadata: reproducible setup, ignored artifacts, offline tests, explicit missing-runtime error, no silent CDN fallback.

These four slices are approved directions, not completed features. Use `/feature-slice` and its reviews for each. Keep the private implementation prompt pack untracked; do not push.

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
