# Freeze reviewed-task identity before inference

Status: implemented and verified; qualification/display policy remains separate. The optional review UI and receipt
API are delivered. This slice connects that authority to future attempts without
changing grades, mastery, scheduling, or historical outcomes.

## Current-code findings

- `orchestrator/grader.py:grade` snapshots assessment content, closes reads, then
  calls `db/assessment_executions.py:prepare` before any gateway inference.
- `prepare` serializes against the workspace claim and writes the durable prepared
  execution. This is the suitable atomic capture boundary, not `apply_result`.
- `orchestrator/assessment_requests.py:_acquire_prepared` reconstructs AttemptRequest
  and verifies its serialized fingerprint against WorkspaceRequest. Adding review
  fields to that request would change recovery identity and risk existing attempts.
- `continue_prepared` deliberately skips preparing another execution; it must reuse
  the original review binding, including an explicitly absent approval.
- `save_grade` persists grade-ready output before `apply_result`; recovery from that
  state must consume the same binding and never fetch a newer approval.
- Existing AssessmentProvenance is version1 and qualification remains not_evaluated.
  Its consumers validate exact fields. Evolving it requires compatibility tests;
  adding a field casually would turn otherwise valid historical disclosure unknown.

## Storage and transaction boundary

Add nullable `assessment_execution.task_review_json` in a named Alembic migration.
SQL NULL means legacy/unrecorded, never permission to look up a review. New requests
store a versioned object with explicit `review: null` when no matching approval is
present. An approved binding stores receipt ID, review revision, task ID, facet,
policy version and private content fingerprint; no source text or hidden answers.
Do not overload owner_json (process ownership proof), request_json (learner intent),
content_fingerprint (existing recovery identity), or grade_json (model grade).

Capture under prepare's write lock. Re-read assessment/rubric/objective and compare
against the grading snapshot before recording the approval binding. If the task
changed since the grading read, fail before inference rather than bind one version
and grade another. Match only the latest learner-owned approval, active task state,
known policy, supported kind, valid rubric and exact content fingerprint.
A concurrent review is therefore ordered before or after preparation; a later
approval never qualifies an already prepared answer. Task-review snapshot JSON and
assessment recovery snapshot JSON are different shapes: do not compare their
hashes directly or extend the old recovery fingerprint to cover the new field.

The original unclaimed/internal grading path may capture an in-memory binding before
inference, but it must never acquire a later approval at apply time. Prefer explicit
unrecorded for unsupported paths until their lifecycle is proven. Never infer review
from item_json, model output, a high grade or previously generated course material.

## Carrying the binding forward

Use a strict private binding schema with version and complete identity validation.
Read the durable binding on prepared continuation and grade-ready recovery; preserve
legacy NULL and explicit no-review unchanged. Copy the validated binding into attempt
result metadata in the same transaction as learning evidence. Keep it distinct from
v1 evidence_provenance until its versioned consumer upgrade is covered by tests.
Malformed/unknown binding must remain unqualified without causing an old saved grade
to be regenerated. Validate owner/task/receipt identity, not a client-provided ID.

Revocation does not rewrite historical receipts or grades. A later display policy
may explain current exclusion while retaining what was approved at submission.
This slice does not yet implement passed labels. All-criterion checks, exact rubric
coverage, help disclosure and model-check disclosure remain separate gates. Showing
reference content during authoring never supports a claim of independent work.

## Acceptance tests before activation

1. Reviewed current task captures the exact receipt; absent/revoked/stale/unsupported
   review captures explicit none. Foreign learner receipts never bind.
2. Approval after prepare cannot change explicit none; revoke/reapprove after prepare
   cannot replace the captured receipt. Concurrent prepare/review has one serial order.
3. Edit between grading snapshot and prepare fails before gateway entry; no evidence
   or scheduler write occurs. Cover task, rubric, objective and practice revision.
4. Prepared continuation preserves binding and original request fingerprint. Legacy
   prepared rows continue unqualified without new review lookup.
5. Grade-ready recovery uses saved grade and binding with zero new model calls;
   legacy grade-ready/completed replay remains unchanged.
6. Unknown/malformed/mismatched binding cannot activate claims or discard a saved
   answer. New client fields cannot inject review authority.
7. Duplicate requests create one attempt/evidence update; rollback and export/wipe/
   backup retain existing guarantees. Disposable migration test before live upgrade.
8. Existing deterministic/rubric/model grading, score, FSRS, mastery and provenance
   disclosure outputs remain identical apart from the separate review metadata.

Run targeted execution/recovery/provenance tests, then full backend lint/format/mypy
and tests; obtain bounded code/pedagogy review. No paid inference is needed. Update
shared handoff and publish paired private/sanitized commits only after verification.

Implementation delta: strict FrozenTaskReview/FrozenReviewIdentity schemas and a
transaction-neutral capture helper now exist. The helper checks the complete review
snapshot (including objective) and returns an exact matching receipt or explicit
none; changed content is rejected. It requires the caller's preparation write lock.
Tests cover absent→approved→revoked capture and task/rubric/objective edits. This
helper is NOT yet called from grading: durable storage, preparation transaction
wiring, continuation/recovery propagation and integration verification remain open.
No migration or grading change was made for this delta. Keep the slice uncommitted
until the durable integration and required reviews are verified together.

Further delta: nullable execution task_review_json column and migration d1a07a70f6ac
added. Autogeneration's unrelated FTS drops/assessment FK rebuild were removed.
Preparation accepts an internal transaction-local capture callback, invoked once
under the claim write lock. New ordinary grader requests check both original recovery
content and full review snapshot under that lock, then store receipt-or-none. Older
callers retain SQL NULL. Re-preparation cannot replace metadata. Callback failures
roll back execution creation without deleting the retained answer claim.

Disposable migration upgrade passes; focused review/execution/prepared-continuation/
crash-recovery tests and strict mypy pass. Live DB is NOT migrated yet. Remaining:
propagate validated binding to attempt metadata on ordinary and grade-ready recovery,
add concurrency/late-review integration regressions, full suite/export/backup checks,
code/pedagogy review, then paired publication. Do not claim labels are enabled.

Propagation delta: apply_result validates only the durable captured binding and its
historical owner/task receipt, then writes separate task_review_binding metadata on
the attempt. It never reads the latest approval or changes v1 evidence_provenance.
Legacy NULL/malformed/unknown metadata remains unrecorded; explicit none survives.
Historical approved receipts remain inspectable after revocation. Current focused
checks include helper restore ownership and a real API submit/replay with a reviewed
task. Full migration/export/backup/integration checks and requested bounded review
are still pending; do not publish or mark the overall binding slice complete yet.

Review follow-up: persisted binding must include schema_version and review explicitly;
missing-version data now fails closed rather than defaulting to v1. New interrupted
prepared-request integration cases prove later approval leaves explicit-none intact
and later revocation preserves the captured historical receipt; 14 continuation
tests pass. Fixture initially lacked a rubric and was corrected to exercise the
supported review path. Full backend suite is running in /tmp/task-binding-full.log;
await its existing process before any rerun. Grade-ready recovery-specific binding
assertions, final review follow-up and publication remain outstanding.

## Final verification (supersedes intermediate pending notes above)

Full backend suite1293 passed with3 existing warnings; after adding integration
cases,22 recovery tests and28 task-review tests passed. These include concurrent
approval ordered behind preparation, prepared/grade-ready later approval/revocation,
no extra grading during finish, missing-version rejection and foreign receipt
rejection. Ruff lint/format and mypy232 passed. Full suite includes export/wipe,
backup/restore and populated migration regressions. Disposable migration check
passed again; live migration applied only afterward. Bounded code/pedagogy review
found no remaining blockers/majors. Private snapshot refreshed for publication.
No frontend/assessment score/scheduler change; existing UI gates are unchanged.

Next: display-only qualifying evidence projection with exact rubric coverage and
current revocation disclosure. Existing v1 provenance and historic attempts remain
unchanged; unrecorded paths remain unqualified. Human understanding and independent
work are not established by a task review or model grade.
