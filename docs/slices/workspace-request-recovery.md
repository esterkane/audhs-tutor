# Workspace request recovery

Status: backend foundation verified; UI identity/retry controls remain pending.

The learner can retry a lost workspace response without paying for another generation.
An optional Idempotency-Key header identifies one exact, learner-scoped request; the server
persists its typed-payload fingerprint before inference and stores the completed response.
Equal identity and payload reopens the original result; changed payload conflicts. Pending or
interrupted requests never silently restart inference. No new learning events or mastery writes
are emitted by replay. All energy modes behave alike; recovery status must be keyboard accessible.

## Contract and lifecycle

- Scope: HTTP workspace tutor, including study feedback. Lesson streams and voice remain separate.
- Database uniqueness, not a process lock, owns the claim. The claim transaction commits before
  network/model calls; those calls retain their independent usage accounting.
- A completed response can be replayed after a process restart or ended session, provided the
  session remains owned. A deleted session/learner cannot be restored through a request key.
- A running record means no terminal result is recorded. It may be executing or interrupted;
  age alone cannot authorize a second generation. The learner can explicitly start new work.
- Failure or cancellation retains the claim; retry reports uncertainty rather than regenerating.
  No claim of exactly-once provider execution, including provider-side retries.
- Records participate in learner export/wipe and private backups. No automatic expiry that would
  turn a late retry into a second generation. Sanitized repositories contain no learner records.
- The key is transport metadata, excluded from prompts and semantic/exact answer matching.
- Frontend must retain the same identity and payload through uncertain delivery, guard callbacks,
  and distinguish Retry from an explicit new request. Browser storage denial must be disclosed.

## Acceptance pending

- [x] Lost HTTP response: replay gives same turn/answer and unchanged model/event counts.
- [x] Concurrent duplicates: one claim and one generation; pending duplicate has explicit status.
- [x] Changed payload conflicts; other learner/session cannot retrieve an answer.
- [x] Restart replay; ended-session replay; deleted-session rejection; export/wipe lifecycle.
- [x] Interrupted inference and failed final persistence never silently regenerate.
- [ ] Client retry/reload identity and stale operations, keyboard recovery journey.
- [ ] Disposable migration upgrade/downgrade, full tests/lint/build, independent review.

Completed-answer save receipts remain a separate mechanism: they recover a delivered answer
whose answer-history insert failed. They do not by themselves recover a lost HTTP response.

## Backend foundation verification

Regression reproduced first: a repeated identical HTTP request generated a new turn and answer.
Six new fake-provider/service tests cover lost response, concurrent endpoint and racing DB
claims, changed payload, cancellation, fresh-connection replay, ended/deleted session and
failed final persistence. Full backend: 568 passed; lint/format/mypy/TypeScript/ESLint passed.
Existing export/wipe and old-schema migration suites passed with the new table. Migration
55d7f6e0304b was generated outside the watched tree, restricted to the intended new table
(excluding reflected FTS tables), reviewed, and upgrade/downgrade tested on a disposable
consistent database snapshot before entering the repository. The live DB was not the test target.
Independent code review reported no blockers/majors. No paid model calls.

Replay after a restart was exercised via a new DB connection, not an OS process restart;
the implementation has no process-local claim state. A recovered response may contain an
expired process-bound save receipt; its separate one-hour/restart limitation remains.
No new frontend behavior yet: optional UUID Idempotency-Key support is an API foundation.
UI integration, reload recovery, storage-denial behavior and browser journeys are next.
