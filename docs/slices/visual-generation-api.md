# Explicit visual generation transport

A learner can explicitly start a local saved-answer diagram, read its saved request
status after leaving/returning, and stop it without deleting an already completed
version. Inputs are an exact AnswerVisualBinding and Idempotency-Key; outputs are
bounded private status fields and saved document/version IDs. No learning events,
grading, scheduling, preference changes, autoplay or automatic read-triggered inference.
This backend slice supplies the next Ask controls; it makes no browser usability claim.

## Behavior

- POST /api/visual-generation reserves and dispatches a pending request. Same key/
  payload returns the same request, while changed payload conflicts. The durable
  worker claim prevents duplicate inference even if duplicate tasks reach it.
- GET by ID and bounded GET by answer are owner-scoped, read-only and never recover
  by starting work. Worker tokens, raw bindings/snapshots and fingerprints are private.
- POST cancel persists the cancellation fence before signalling the process task.
  Completion that won the save race remains readable. In-flight transport cancellation
  is best effort; the durable fence prevents publication or another attempt.
- App-scoped handles retain workers across client disconnect; each worker has its own
  gateway session. Clean shutdown cancels/joins them before DB disposal. Startup's
  existing reconciliation marks abandoned pending/running requests interrupted.
- Request input is byte-capped before parsing; invalid content is not echoed. Model
  errors are not logged verbatim. No new table, dependency or multi-user auth claim.

## Verification
Five focused route/concurrency/shutdown tests passed; full backend: 1553 passed
(3 existing warnings). make gen-api and make lint passed. Required bounded code
review found no blockers/majors. Tests use disposable SQLite and fake providers;
no live-model inference or paid calls. Existing UI code is unchanged.
Ask controls and local-model semantic evaluation remain outstanding.
