# Recover a completed answer after saving fails

Status: implemented and bounded acceptance passed.

At 6cbba9d a completed reply could be delivered with `save_error`, but the learner could only keep a manual copy or generate again. This slice adds Retry saving without a new model call. The original immutable turn, supplied work, text and metadata are retained; no grade, checkpoint or learning evidence is replayed. The same control is used in study feedback, lesson sources, standalone workspace and saved-answer follow-ups.

## Contract

- On a completed-answer database save failure, return a bounded signed receipt containing the server's original save snapshot. The application holds only a random process-local HMAC key; no pending-answer global cache or new database schema. Partial turns never get a receipt.
- Receipt lifetime is one hour and ends on backend restart. The receipt is authenticated, not encrypted: it stays in the local client alongside the reply, and is never sent to a model. A text-copy download remains available if recovery expires or exceeds the receipt size limit. This is not guaranteed recovery across restart, lost HTTP delivery or leaving a surface without a retained reply.
- Retry verifies signature, expiry and learner identity before accepting a snapshot for persistence. The save still verifies that the session exists and belongs to the learner; wiped/deleted sessions cannot be resurrected. It accepts no replacement text or metadata from the client.
- Equal turn and equal snapshot uses the existing database uniqueness/fingerprint contract and returns the same answer ID. A mismatched snapshot conflicts. Concurrent retries and a lost acknowledgement after commit cannot create another answer. Retry emits no new tutoring/learning events and invokes no generation. Full-text search becomes available through the existing database trigger. Recovery schedules no embedding or generation; semantic indexing waits for the next normal indexing pass.
- UI request identity and cleanup prevent late saves from updating another turn. A 15-second timeout keeps the reply and allows retry. Follow-up conversations resume from the recovered answer ID. The action explicitly says no new model call; errors never erase visible text.

## Acceptance

Tamper/owner/expiry/restart/size checks; injected save failure with and without a prior commit; concurrent retry returns one ID and unchanged model-call count; deleted-session rejection; complete-only stream receipts; UI timeout/unmount/stale response and successful recovery; backend/voice propagation; isolated browser keyboard and narrow-screen checks. Preserve existing report/CAS and learner export/wipe behavior. Relevant suites, lint/build and independent code/pedagogy review precede paired publication.

Open beyond this slice: request-level inference idempotency and recovering an answer when the response itself was never received. The receipt does not claim exactly-once model execution. Persistent encrypted recovery across backend restarts remains separate.


## Verification — 2026-10-01

Full backend suite: 561 passed; final complete/partial recovery regressions: 6 passed. Full frontend: 236 passed; final timeout/voice/follow-up checks: 18 passed (including the added partial-voice test). Lint/format/mypy/TypeScript/ESLint and production build passed. Two isolated desktop/narrow Chromium journeys exercise keyboard save retry, one generation only, recovered link and retained answer. Desktop screenshot inspected. Fakes/disposable data only; no paid API calls or Bluetooth-hardware validation.

Independent review fixed two majors: timeout now releases the UI even when a transport ignores abort, and voice now retains the completed snapshot and exposes recovery. A real rollback test also required capturing the tutor trace ID before ORM expiration so the original completed answer is delivered. Partial lesson/voice results never receive recovery controls. No remaining code/pedagogy blockers or majors.

Previous private-archive CI passed. The sanitized run failed an existing timing-sensitive follow-up test that clicked while the new parent's feedback query was pending; the test now waits for Send to become enabled before clicking. This is included here because the same follow-up is part of the recovery flow. New CI is required after publication; do not call the previous sanitized run green.
