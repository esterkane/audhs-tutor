# Progress task eligibility — implementation boundary

2026-10-12. Engineering proposal for the owner-approved task-specific display scope.
This is not an accepted ADR or permission to change grading/scheduling. Read alongside
PROGRESS-EVIDENCE-CONTRACT.md and the delivered provenance/context slices.

## Concrete gap found in the current implementation

Assessment.kind identifies interaction type, not what capability the task tests.
AssessmentRubric stores criteria and a version, but no review decision or objective
qualification. Explain-back can test recall rather than reasoning; a transfer tag
does not establish independent application. The existing model grader checks exact
criterion identities and nonempty evidence; those checks validate response shape,
not whether the authored rubric measures the intended objective. Keyword checks are
routing diagnostics and cannot qualify explanation success.

Correction publication creates a new assessment and rubric and supersedes the old
question. A qualification flag copied into item_json would be unsafe: generative
content could set it, correction validation forbids unrelated candidate keys, and a
replacement could inherit approval for different content. Eligibility must remain
server-owned, outside generated item content, tied to exact reviewed content.

## Next coherent implementation

1. Add a learner-scoped review receipt, separate from Assessment.item_json. Store
   task ID, exact private content/rubric fingerprint, explicit facet (explanation or
   application), policy version, review time and review decision. Use immutable
   receipt IDs and an explicit superseding/revocation record. No default eligibility,
   imported approval, model-generated review receipt or historical backfill.
2. Provide a read-only review preview of the exact question, objective, rubric and
   sources. Explicit confirmation creates the receipt with an optimistic content
   guard and repeat-safe request ID. Describe this as an author/learner review,
   not an independent educational validation. Editing/publication creates a new
   question that needs its own review; existing old records stay inspectable.
3. Freeze the applicable receipt/policy identity when the accepted grading request
   is prepared, before inference. Persist an explicit no-eligible-receipt state;
   absence must never mean “look up the latest review during recovery.” A prepared
   continuation reuses that frozen identity, including none, and copies it atomically
   into the final attempt. Legacy prepared requests and schema-version1 snapshots
   remain unqualified. A review performed later cannot retroactively qualify that
   work. Later revocation adds a current exclusion without rewriting the historical
   identity. Keep eligibility metadata separate from the existing recovery content
   fingerprint; do not change old snapshot serialization or strand prepared grades.
4. Derive display labels deterministically from the saved receipt and exact criterion
   results. Do not classify using aggregate CompetencyEvidence.score. For an eligible
   explanation task, every required reviewed criterion must have an identified,
   nonempty recorded check and pass. Keyword-only routing cannot qualify success.
   Application attempted and check-passed remain different facts. Unsupported code
   execution provenance retains the current unqualified record until independently
   covered; running a notebook alone is never an application check.
5. Preserve saved result/date/help disclosures, grader identity and revision lineage.
   Immediate revised work can show its task result in history but must not create
   another competency/FSRS row or imply independent demonstration. Later suspension,
   correction, revocation or incompatible policy retains the historical result with
   an exclusion reason instead of silently deleting or currently endorsing it.
6. Render the approved task-specific labels and reason inside existing Progress.
   No new badge ladder, percentages, model calls on reads, recommendation engine,
   gating changes or new frontend dependencies.

## Required touch points and tests

- DB model/migration, learner export/wipe and backup/restore: empty/upgrade paths,
  owner isolation, historical receipts, restore and FK ordering. Inspect the current
  generic learner-table handling; do not assume it handles new dependencies.
- Dedicated schema/kernel/API receipt workflow: content races, duplicate commands,
  foreign task/review, revocation and exact snapshot binding. Keep correction
  candidate schema strict; don't overload correction publication as approval.
- Grader/provenance: original and prepared continuation, rollback/concurrent finish,
  changed content, review/revocation between preparation and recovery, explicit-none
  eligibility, model-supplied fake qualification, unknown policy/version and absent
  criteria. Existing claim/recovery tests remain mandatory.
- Progress: approved failed/partial/all-criteria results, unknown/legacy records,
  duplicate/revised work, disputed/retired/replaced tasks, stable pagination/dates
  and read-only competency/FSRS. No eligible data means no qualified label.
- UI: explanation of what review approves; explicit confirmation/recovery, keyboard,
  narrow/dark/zoom, saved feedback navigation and human comprehension. Never imply
  learner review establishes independent work or external validation.

## Policy boundary before activation

The owner approved label wording, disclosure, display-only behavior and explicit
task/rubric review authority (decision below). Review receipts alone do not activate
attainment claims: preview/confirmation and frozen pre-inference eligibility must
be implemented and verified first. The shipped task/help disclosure remains active.

Design review: identified and resolved the prepared-recovery timing gap above.
Implementation must freeze eligibility before inference; selecting current approval
at grade application could incorrectly qualify earlier work. No code or learning
state has changed as part of this design review.

Owner decision2026-10-12: “Use explicit task/rubric review.” Only explicitly
reviewed objectives/rubrics qualify; generated/imported tasks remain unqualified,
edits need fresh review, model checks stay identified and independence unverified.
This authorizes the review-record workflow. It does not make earlier attempts
qualified or enable grading/scheduling changes. Receipt storage is the first slice;
preview/confirmation UI and pre-inference frozen eligibility follow.
