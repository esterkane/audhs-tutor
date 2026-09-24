# Session clarity and learner control

- Story: learn within the selected area, with context and optional questions; stop or change topic freely.
- Inputs/outputs: area/course selection, optional confidence, clear/later material marks, question-specific help and local read-aloud.
- Events: existing attempts, session/block endings and TTS model calls; material marks are explicit preferences, never competency evidence.
- Mode/energy: preserve learner choices and soft timers; no assessment or rating is required to stop.
- Accessibility: labelled controls, optional details, keyboard support, no automatic audio.

## Reproduction before changes
Select Python on Home while it has only draft lessons. The planner falls through to the seed graph and shows Dot product as similarity. A current session also retains its old active skill. In an assessment, Check my answer is disabled without confidence; no inline help or audio exists; Stop and recap leads to further ratings.

## Acceptance
- Selected areas without active lessons show an activation link, never unrelated fallback.
- Confidence is optional and omission remains null, without synthetic calibration.
- Stop and change topic require no question or recap; completed work remains saved.
- Clear/later labels persist as self-report, without changing mastery.
- Questions have lesson context and inline hint/explanation; local read-aloud is opt-in and stoppable.

## Review fixes
Required code and pedagogy reviews found hidden audio, lost hint history, unsafe storage, divergent selection snapshots and a broken recovery link. Fixed: audio/voice unmount on phase exit; first delivered help persists with the assessment draft; storage exceptions cannot hide a successful grade; one resolved selection feeds plan/checkpoint; empty-area links preselect the area and empty-course links use `/curriculum`.

## Limits
Clear/later bookmarks are explicit reminders and can be revisited on Home; they are not automatic FSRS ratings. A browser draft is best-effort tab storage, with memory fallback. Lesson audio uses the existing local Kokoro service; the UI labels its English voice. No unpublished area draft is silently activated. Historical open sessions retain their original topic; use Change topic to end them and choose a new one.

## Local tutor evaluation
The old base and final pedagogy.v2 each passed 3/5 hard checks in one local Gemma run. Old: recap and negated-solution brevity failed. New: QKV explanation and negated-solution brevity failed; hint withholding and Socratic checks passed in this run. These are limited single-run observations, not proof of equal quality. A discarded broader wording change scored 2/5; it is not shipped. `evals/results/session-clarity-comparison.json` records the final comparison. No hosted model/key was used.

## Verification
Verification: 374 backend tests, 63 component tests, 10 isolated Playwright journeys, generated API types and lint passed. Browser screenshot inspected. Required code and pedagogy re-reviews report no remaining majors. Tests use fakes/disposable data; the local 3/5 tutor comparison remains a separate incomplete quality gate.

Early-stop follow-up: session end only schedules a first recall item after a non-empty explanation event on that session/skill. Negative and positive regression tests preserve this boundary. GitHub first caught a macOS-only screenshot path; the portable Playwright output-path fix passed all four CI jobs (run 35989913285).
