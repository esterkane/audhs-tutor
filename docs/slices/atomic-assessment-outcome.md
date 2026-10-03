# Recoverable committed assessment outcome (R3 / F04)

A learner whose response is interrupted after grading must recover the original outcome without
regrading. The request outcome and immutable history snapshot now commit with the learning write set.
Lookup/replay reads history status and, if necessary, issues a fresh save-only receipt from the snapshot.
No new learning events or inference on recovery; no schema, confidence, mode or energy changes.

## Implementation
- Grader receives the trusted owned claim ID from assessment submission and finalizes it with
  commit=False before the single learning commit. Missing claim or completion failure rolls back learning.
- The private request JSON includes a versioned internal history snapshot, excluded from API results.
- Searchable feedback still saves separately. Failure/cancellation after learning commit can no longer
  strand a committed attempt behind an unresolved claim. Replay links existing history, avoiding duplicates.
- An unsaved snapshot can receive a new signed receipt after restart/expiry; lookup itself makes no DB writes.
- Legacy completed request rows remain readable. Existing unresolved rows are not guessed or repaired.

## Verification
Pre-fix regression: interruption after grading returned 409/unresolved despite a committed attempt.
Focused request/history/atomic tests27 passed; expanded request recovery7 passed. Tests include cancellation
before/after history save, new signing key, original snapshot after question editing, save-only recovery,
no extra attempt/evidence/review/model writes, rollback on claim completion failure and owner/session scope.
Full backend636, focused UI16, desktop/narrow browser journeys2, lint/types and production build passed. Required code and pedagogy reviews cleared blockers/majors. The review wording minor was fixed: adopted feedback now says mastery/review scheduled after this attempt, not current state. Existing library and bundle-size warnings remain.

## Limits
Unresolved claims from before the learning commit still require explicit handling, never automatic regrading.
No exactly-once model execution claim. Legacy unkeyed callers lack request deduplication. Oversized snapshots
may exceed the existing signed receipt limit; visible feedback remains available. Review-rating idempotency
and assessment content-version conflict guards remain open. No live learner-data edits or paid calls.
