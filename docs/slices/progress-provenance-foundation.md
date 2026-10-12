# Progress provenance foundation

Owner approved dated task-specific display labels, help disclosure and independence
unverified on2026-10-12; grading, gating and scheduling remain unchanged. Before
labels, retain the facts needed to assess eligibility for each exact attempt.

New grades attach a schema-version1 evidence_provenance object inside the existing
private deterministic/model result JSON: task kind, guarded content fingerprint,
rubric version if available, grading method, client-reported hint count and resolved
root-revision ID. It explicitly records assistance coverage as partial, external help
unknown, full-solution exposure not recorded, independence not verified and label
qualification not evaluated. Model output cannot set these facts; construction occurs
after model validation and revision resolution inside the existing learning transaction.

No migration, API field, UI, model call or additional event is introduced. Saved grade
recovery uses the same application path. Legacy rows remain without the field; do not
backfill qualifications. Fingerprint identifies the exact task/rubric content but is
not itself a reviewed-rubric eligibility declaration. No independent-work claim follows
from zero hints. Negative legacy/client reports are preserved raw; this foundation
must not tighten existing request validation or strand accepted recovery requests.

## Verification
Targeted tests cover deterministic and mocked model grades, immutable captured facts
after question edits, revision root identity and unchanged learning rows, full rollback,
idempotent replay, prepared continuation and concurrent grade-ready finish. No hosted
calls. Strict mypy from backend (using its configured Pydantic/stub settings) passes229
source files. An initial invocation from repo root omitted that config and reported10
unrelated errors; it is not the authoritative configured check. Ruff passes.
No new visual/browser claim: this internal metadata slice does not change rendering;
existing tested assessment flow is unchanged. Final test count/review recorded below.

## Remaining
A validated read model with learner/content/version checks and an explicit unknown
fallback; task/rubric eligibility policy identity; fuller observed-help provenance;
reviewed labeling semantics and shared Progress UI. New labels are not enabled by this
foundation. No arbitrary score threshold is adopted and no policy is inferred from
model feedback. Future display reads must treat missing/invalid/future snapshots as
unknown rather than infer successful understanding.

Final69 targeted tests pass12.81s. Code/pedagogy review found the negative-hint
compatibility issue; fixed and regression-tested through application/replay and
concurrent recovery. Follow-up review found no remaining actionable findings.
