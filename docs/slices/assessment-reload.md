# Checked assessment reload recovery

## Contract — 2026-10-05

A completed grade survives in server request outcomes, but successful delivery clears the pending-submission record. Reload then loads the next question rather than the checked question. Extend the existing in-page retention with a tab-local, activity-scoped return pointer: original request UUID, assessment/attempt identity, and the exact displayed question snapshot. No grade is stored as browser authority.

On re-entry, read the original outcome through the existing read-only request endpoint. Match assessment, skill and attempt identity before rendering. Never call submit/finish automatically. Missing, unresolved, failed or mismatched reads show an explicit recovery state; they must not silently start a new question. An explicit next-question action clears the return pointer. Legacy sessions without a pointer continue using existing behavior. Storage corruption/failure stays visible. Partial submission recovery remains separate and must not be cleared by this return pointer.

Likely files: assessment submission callback, new small return-pointer hook, Session panel and focused tests. No backend schema, grading, provider, FSRS or competency change. Full reload retains server-confirmed feedback and exact question context; original saved mastery/review values remain historical, not current evidence.

## Implemented and verified

Both desktop and narrow pre-fix journeys failed on missing feedback after reload. The implemented pointer is versioned and keyed by session, block index, block start and skill. Its bounded question snapshot is separate from pending submission recovery. Successful delivery and explicit acceptance of a recovered result can save the pointer. Assessment remounts on scope changes. Restored local continuation readiness derives from the original server result, without another learning write.

Thirty-six focused unit checks pass: request recovery, Session and the new pointer hook. Tests cover exact original-result GET, wrong/missing/unresolved outcomes, activity/skill isolation, corrupt storage, failed writes/removal and a late response after leaving the checked question. Seven Chromium journeys pass: real wrong-answer→explanation→reload at390/1280, temporary503 lookup and keyboard Retry, no next-question read until explicitly requested, no extra grading call, plus interrupted explanation/session clarity/visualizer recovery regressions. Full lint, TypeScript and production build pass. Existing worker_threads externalization/bundle-size warnings and unit canvas warning remain.

Narrow restored feedback inspected visually: original question and correction readable, historical-result message visible, Continue/Revisit/optional next question accessible without horizontal overflow. Keyboard activation restores feedback and retries a failed read. Independent code/pedagogy review found no actionable defect; its failed-removal and late-read coverage suggestions are now included.

## Limits and next work

Older sessions without a return pointer cannot restore this way; existing saved feedback remains the archive. Browser storage denial is explicit, not a promise of reload recovery. A reply lost before successful delivery stays in the existing unresolved-submission workflow. This slice does not prove repeated-error adaptation, model-feedback correctness, physical audio or owner comprehension. Next inspect broader pending-submit/navigation and uncertain-transition messages, then repeated-error guidance. No hosted inference or learner database was used in browser tests.
