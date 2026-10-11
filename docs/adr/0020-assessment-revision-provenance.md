# 0020 — Durable provenance for revised assessment practice

Status: provenance foundation implemented; revised-practice evidence policy and
endpoint/UI remain pending. Context: owner-requested complete design system p10
and `docs/design/PRACTICE-RETRY-CONTRACT.md`.

## Decision implemented

Record the existing stable server-only assessment recovery fingerprint on new
assessment attempts. Add a nullable original-attempt foreign key for the forthcoming
revision relationship. Existing attempts retain null rather than invented historical
content identity. These values are not exposed as answer-derived public content tokens.

Validate roots against learner, active session, assessment, original-versus-revised
status and current eligible content. Unknown legacy provenance is not safe evidence
of an unchanged question. Read fresh session/root state on revalidation; final runtime
integration must invoke validation under the existing serialized content-write guard.
The helper does not acquire that write lock or enable revision submission itself.

The migration adds nullable columns without rewriting historical attempts. Foreign-key
integrity is tested; downgrade refuses to discard populated revision relationships.
No grade, competency, FSRS, routing or UI behavior changes in this foundation.

## Pending policy and integration

The proposed distinction between immediate assisted revisions and later independent
attempts remains in the retry contract. Implement transactional application and
idempotency checks before exposing new request fields or UI actions. Keep original
attempts immutable, retain revised work in history, and explicitly label scheduling
and evidence effects. Do not use a hint count as a substitute for this distinction.

## Evidence

32 revision-root, existing request-recovery and migration tests;19 backup/restore
and encryption tests; strict mypy on the3 changed modules and targeted Ruff pass.
Code review identified stale identity-map reads; explicit refresh and a two-connection
regression resolved it. Bounded code/pedagogy reviews are clear. No UI change, no live
model calls, and no claim that the retry interaction is complete.


## Explicit revision application — 2026-10-11

The existing assessment request accepts an optional original-attempt ID. The explicit
path validates the root before inference and again under the serialized content-write
transaction; it saves a new attempt, events and searchable feedback but skips competency
record/refresh and FSRS updates. Results identify the root and whether review was updated.
Saved text and Session result copy label revised practice and unchanged scheduling.
Replayed and already-graded requests retain their original identity even after session
end; newly submitted revisions require an active session. Legacy null-field fingerprints
remain compatible in submission and prepared-request recovery.

Attempted/graded events carry attempt and revision identity. Experiment error/latency
comparisons exclude flagged revisions. Reviewer-found metric contamination was fixed
with a regression. Tests cover repeated explicit revisions, immutable original answers,
exact replay, parent rejection, failed commit rollback and once-only finish after end.

Evidence:57 backend revision/request/finish/prepared/experiment checks pass with a clean
process exit;13 UI component and2 keyboard/responsive browser checks pass. API types
regenerated, targeted mypy/Ruff/ESLint and production build pass; desktop/narrow screenshots
inspected and code/pedagogy reviews clear. One earlier test process crashed in native
teardown after printing passes; the later combined57-test process exited0.

Remaining: missing-parent classification across existing callers, original-answer retrieval,
durable revision draft and Try again/Next UI. Ordinary submissions without a revision ID
still use existing semantics; this is NOT the complete retry policy or a finished user flow.
No new paid-model usage; deterministic fixtures verified these paths.

Additional regression evidence:23 grading-atomicity/database-core checks pass.


## Automatic repeated-practice classification — 2026-10-11

The grader now resolves omitted revision parents from the earliest owned ordinary
attempt with the same session, assessment and stable content fingerprint. Resolution
runs before inference and again under the content-write lock. The effective parent
is applied only to the committed attempt/result/history; raw claim and staged-request
identities remain unchanged, preserving recovery/replay. Two concurrent distinct
request IDs produce one original and one revision. Later sessions remain ordinary
attempts; this boundary is not proof of independent recall. Unknown legacy roots fail
closed with a retained-answer/new-session message rather than inferred provenance.

All result surfaces using AssessmentSaveStatus now share the repeated-practice notice;
code explain-back also includes it. Challenge scheduling copy reflects review_updated.
Wording describes a previously checked question without claiming the learner read
feedback. No save handler or learning progression action was changed.

Evidence: full backend1141 tests pass with clean exit.41 existing surface component
checks pass;11 focused notice/code checks pass after the final shared-notice extraction
(two are new notice checks). Two final keyboard/responsive browser checks and screenshot
inspection, mypy/Ruff/ESLint/build and code/pedagogy reviews pass. Initial full-suite
failures exposed legacy payload fixtures that included a new absent field, plus listening
expectations for duplicate evidence. Fixed historical shapes and asserted listening keeps
two attempts with one evidence/schedule update. Ordinary rollback tests now use a later
session while preserving prior memory rows. No model calls or live learner attempts.

Remaining: owned original-answer retrieval, durable edit/cancel/reload revision state,
and Try again/Next actions. The backend repeat policy is active; the full PDF Practice
interaction and human/assistive-technology acceptance are not complete.
