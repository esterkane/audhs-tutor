# Learner-scoped block and replan endpoints

Six API handlers previously accepted a session belonging to another learner: block state, start, end, next, extend and replan. Baseline HTTP tests reproduced all six returning success for a foreign session ID.

The handlers now use the existing `session.get_owned` lookup with the current `Learner` dependency before reading state or invoking the kernel. Foreign and missing IDs return the same 404 response. No request/response schema, kernel decision, grading, scheduling, transaction boundary or UI changes are introduced.

## Verification

- Six regression cases verify identical foreign/missing responses and unchanged whole-database snapshots.
- 45 affected backend tests pass, covering owned-session transitions, extension/replan, atomic next activity and session completion.
- Full lint/type checks pass.
- Code and pedagogy reviews found no actionable issue.
- 16 isolated browser journeys pass: pause/resume, Back/Forward, delayed/uncertain transition responses and stop/navigation. Keyboard and 390/1280px cases pass; resumed desktop/narrow screenshots visually inspected. No UI code changed.

## Limits

This enforces the existing current-learner resolver; it does not introduce multi-user authentication. Direct start/end/extend/replan lifecycle concurrency with Finish remains a separate validation task. No broader security or learning-quality certification is claimed.
