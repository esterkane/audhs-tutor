# Practice retry contract — 2026-10-11

Status: implementation plan; runtime behavior is unchanged. Target: complete design
system PDF p10, outcome-based Try again / Next. This records the architectural issue
before expanding the presentation work into assessment persistence.

## Current evidence

- `frontend/src/routes/Session.tsx`, AssessPanel: `nextItem` clears the checked-question
  pointer and fetches the next item. It is not a same-question revision. The submitted
  answer draft is cleared after success. A restored result has no editable answer in
  the checked-question pointer.
- `features/assess/useAssessmentSubmission.ts` assigns a fresh UUID to each deliberate
  submission. An unresolved request blocks a new submission. Lookup/replay retains the
  old UUID and must never be repurposed to submit a revised answer.
- `backend/app/schemas/grading.py`, AttemptRequest: no prior-attempt or revision field.
- `backend/app/orchestrator/grader.py`, `_apply_result`: each new successful request
  writes an attempt, competency evidence and a memory review. Hint count affects the
  memory rating, but is not passed into competency evidence weighting. Increasing hint
  count alone would not establish a safe revised-answer evidence policy.
- The current result threshold (0.85) enables continuation readiness. It must not be
  silently replaced by a new UI threshold. Learners can still leave or continue after
  an unsuccessful attempt; retry must remain a choice, not a progression gate.

## Intended learner flow

1. Keep the current question and checked feedback together. For an unmet outcome,
   offer primary Try again and retain a secondary Next action. For a met outcome,
   primary Next; preserve optional further practice and revisiting the explanation.
2. Try again opens the SAME content version with the prior submitted answer editable.
   Keep original feedback accessible under a disclosure; focus the answer control.
   Explain before submission that this is practice after seeing feedback.
3. Check my answer checks the revised work. The original attempt stays immutable and
   accessible; never overwrite its answer, result or saved-answer reference.
4. Refresh, Back, topic changes and leaving must preserve the revision draft and
   original-attempt relationship. Cancelling a revision returns to original feedback.
5. Retrieval failures or a superseded/excluded question preserve the draft and explain
   the recovery path. Never silently switch a revision to another question/version.

## Bounded implementation sequence

### A. Server contract and evidence policy

Add an optional explicit prior-attempt relationship, validated by learner, session,
assessment and content version. Reject foreign, unavailable or incompatible parents
before inference. Persist the relationship with the attempt, recovery intent and
saved feedback. Generate API types from the schema rather than hand-editing them.

Proposed policy for review before implementation: an immediate revision is assisted
practice, recorded with its rubric feedback but not a second independent competency
or FSRS update. A later scheduled attempt remains an ordinary assessment. Do not
implement this by fabricating hints or changing a score. Review this policy against
existing progress evidence and write the applicable ADR before changing the kernel.

### Revision boundaries and progression (proposed)

- The root is an owned ordinary attempt for this assessment/content version in the
  current active session. Every revision points to that root, never another revision;
  preserve each revision as a separate immutable history entry. Reject cycles and
  revision-as-root inputs. Reload does not end eligibility; ending the session does.
- Recovery of an already accepted revision remains available after session end using
  its existing identity. Ending the session rejects NEW revision submissions, not
  result lookup or replay. A new session's scheduled assessment is ordinary practice.
- Enforce classification server-side: a repeated check of the same item/version in
  the same session after delivered feedback must not evade assisted status merely by
  omitting the parent field. Resolve the root from owned history or reject with an
  actionable revision-required response. Verify existing callers before enabling this.
- A successful revision may satisfy the existing0.85 activity-continuation readiness
  check, but this is readiness to move on, not independent mastery. Failure never
  removes the learner's exit or secondary Next option. Preserve any prior readiness.
- Result and history label this as revised practice after feedback. Show the existing
  review due date with unchanged-schedule wording; never say the revision scheduled
  a new review. Keep the original attempt and feedback accessible.
- Add repeated-revision, root-validation, missing-parent, reload, ended-session replay
  versus new-submission, and later scheduled-attempt tests before merging the policy.

### B. Durable revision UX

Retrieve the owned original submission, preserve a versioned local revision draft,
and reuse existing submission/recovery machinery with a NEW idempotency key for a
new revision. Never discard an unresolved old request. Do not add another client
learning-state owner. Handle restored results as well as same-visit results.

### C. Actions and help

Wire Try again / Next to these defined operations. Retain sources, question reports,
answer history, explanation, hints, optional confidence and exits. Reconcile the
remaining PDF secondary help controls using existing endpoints. Do not label a
concept explanation or different exercise as a same-question retry/full solution.

## Acceptance gates

- Same UUID replay: exactly the same result, no extra attempt/evidence/review.
- Revised answer: distinct UUID and immutable parent; double-click has one effect.
- Foreign/wrong-session/wrong-version/excluded parent rejected before model work.
- Lost response and reload restore the correct revised request; no automatic grading.
- Verified revision policy leaves baseline evidence/review unchanged where specified,
  while retaining the actual revised answer and rubric feedback in history.
- Original and revised answers remain distinguishable in search and saved feedback.
- Empty/failed storage, changed question and unavailable original answer retain work.
- Keyboard focus, narrow/desktop reflow, dark theme, text scaling, reduced motion,
  source access and learner-controlled exit checked in the sandbox.
- Human and assistive-technology acceptance remain explicit, not inferred from tests.

Do not declare the PDF Practice blueprint complete from the preceding feedback-order
slice. This contract is the next implementation boundary, not a completed feature.


2026-10-11: Revision provenance foundation implemented (ADR0020): new attempts record stable content identity; nullable original-attempt relationship and read-only root validator added.32 migration/recovery/root and19 backup tests pass; mypy/Ruff and reviews clear. Legacy provenance stays null. No revision endpoint/UI or changed evidence policy yet; next connect serialized application and replay before exposing controls.


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
