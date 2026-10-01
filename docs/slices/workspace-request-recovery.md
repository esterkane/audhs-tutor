# Workspace request recovery

Status: workspace API and Study Tutor/Playground UI implemented and verified.
Saved-answer follow-ups, lesson streams and voice request identities remain separate work.

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
- [x] Fresh-connection replay; ended-session replay; deleted-session rejection; export/wipe lifecycle.
- [x] Interrupted inference and failed final persistence never silently regenerate.
- [x] Client retry/reload identity and stale operations, keyboard recovery journey.
- [x] Disposable migration upgrade/downgrade, full tests/lint/build, independent review.

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
At the foundation commit, frontend identity handling was still pending. The UI completion
and its separate verification are recorded below.

## 2026-10-02 — UI recovery

Study Tutor and Playground now freeze the full submitted request, UUID and original display
context in tab-scoped session storage before sending. Retry previous request restores that exact
payload after a failure, Stop or reload. Editing work does not silently replace an unresolved
identity: the learner explicitly discards its retry before sending different work. Returned
study feedback uses its original snapshot, preserving the earlier-feedback label after edits.
Request metadata never enters tutor prompts; normal routing and disclosure remain unchanged.

Storage write failure retains the identity in memory with a reload warning. Unreadable stored
records require explicit discard. Completely inaccessible storage offers explicit Continue
without reload recovery; this clears only in-memory retry state and warns that older saved
state may reappear after reload. Closing a tab, cleared browser data, or denied storage cannot
be represented as durable browser recovery. Stored retry records contain private submitted
material in the browser, not in either repository. No automatic resubmission on mount.

Verification: full frontend241 tests passed before the final storage-denial fix; final focused
35 tests passed including that fix. Full lint/mypy/TypeScript/ESLint and production build passed.
Five isolated Chromium journeys cover desktop/narrow Study Tutor and Playground lost-response
reload recovery, keyboard retry, identical UUID/payload, one simulated generation, overflow,
and fully denied session storage with explicit in-memory continuation. Narrow screenshot
inspected. Providers are faked; these journeys do not claim real-model latency or quality.

Review fixes: required code review found completely denied storage could permanently block new
work; explicit in-memory continuation and all-methods-denied regression fixed it. Re-review
found no remaining blockers/majors. Pedagogy review found no major issue; stopped/retry copy
now names original answer/code/material and distinguishes edited work. No backend changes in
this UI slice; preceding full backend568 and both foundation CI runs passed.
