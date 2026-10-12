# Explicit task review receipts — foundation

Owner-approved2026-10-12: task/rubric review is explicit; generated/imported tasks
remain unqualified and changes require a fresh review. This slice stores authoring
review decisions, not assessment results or a claim of independent validation.
Inputs: learner/task, exact preview token, expected revision, request UUID, facet,
approve/revoke and explicit confirmation. Output: immutable-by-service receipt.
No learning events, scores, scheduling, mode/energy changes, API or UI activation.
Accessibility and preview/confirmation interaction follow in the UI slice.

The new learner-scoped table binds decisions to task, rubric, objective and practice
revision, outside model-generated item_json. A serialized write lock plus unique
owner/request and owner/task/revision constraints prevents concurrent duplicate
receipts. Replays return the historical receipt; changed request IDs/revisions or
content are rejected. Revocation appends another receipt; it does not rewrite history.
Supported review currently requires a nonempty, distinct textual rubric on the
existing explanation/transfer/challenge kinds. Code execution review is deferred.

Migration4ab714cf670c adds only this table/indexes and refuses downgrade with review
history. Autogeneration against the outdated default DB was refused, then run against
an upgraded disposable DB. Unrelated FTS drops and an existing FK rebuild proposed by
autogeneration were removed before testing. `make migrate-check` upgrades a consistent
disposable copy successfully. The live database has not been migrated by this slice.

No grade consumes these receipts yet. The next slice must expose exact read-only
preview + explicit confirmation and freeze the receipt or explicit-none in accepted
request preparation before inference. Never look up a later review when recovering
an older grade. No historical attainment-label backfill.

Review follow-up: receipts now retain the exact task/objective/rubric snapshot,
not only its fingerprint, so later edits do not erase what was reviewed. Unicode
preview tokens produce a controlled conflict. Concurrent distinct commands cannot
both claim the same revision; suspension/restoration invalidates old previews.
Verification: 17 focused receipt tests passed; full backend suite 1280 passed
(3 existing warnings, 101.39 seconds). Ruff lint and format checks passed (418
files), strict mypy passed (231 source files). Repeated `make migrate-check`
reached 4ab714cf670c on a disposable consistent database copy. No live migration.
Bounded code/pedagogy re-review found no remaining blockers or majors.
No browser interaction changed; preview/confirmation accessibility and UI checks
remain for the next slice. No API/UI qualification is active.
