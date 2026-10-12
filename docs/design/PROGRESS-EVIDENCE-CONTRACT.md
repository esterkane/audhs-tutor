# Progress evidence labels — contract before implementation

Status: owner approved the first display scope on 2026-10-12: task-specific, dated
evidence labels with disclosed help and independence unverified. Detailed eligibility
metadata remains to be implemented; no new evidence levels are active.
Authority: owner-supplied Complete Design System, pages8 and10. Existing boundaries:
ADR0004 (memory versus competence), ADR0020 (revision provenance).

## Problem and current evidence

The design calls for Encountered, Understood, Practised and Demonstrated states,
with dates and an inspectable explanation. These words are claims about learning;
renaming a score or a count would not implement the design accurately.

Inspected current sources:

- `backend/app/db/models.py`: CompetencyEvidence records dimension, score, weight,
  grader, source attempt and date. AssessmentAttempt records content fingerprint,
  revision parent, answer, result, hint count and date. Neither provides complete
  assistance or independent-work provenance.
- `backend/app/orchestrator/grader.py`: original assessed attempts add competency
  evidence; immediate revisions retain their history without adding another such
  row. Do not count these revisions as repeated independent demonstrations.
- `backend/app/kernel/competency.py`: decayed weighted aggregates support the existing
  kernel. They are not validated thresholds for the proposed display vocabulary.
- `backend/app/kernel/progress.py`: a read-only, learner-scoped evidence view joins
  owned attempts and saved assessments. Dimension summaries count all evidence,
  including unsuccessful checks; a nonzero count cannot mean Understood.
- `backend/app/schemas/progress.py`: independence is explicitly `not_verified`.
- `frontend/src/routes/Progress.tsx`: records and dates are shown without declaring
  mastery; Independent application remains unverified. Preserve this honest fallback.
- `backend/tests/test_progress_evidence.py`: missing/foreign attempt provenance,
  zero hints and a full-credit transfer check do not certify independent work.

## Required semantics

| Display state | Evidence required before enabling it | Insufficient on its own |
| --- | --- | --- |
| Encountered | A defined, dated exposure event tied to this concept and content version; label it exposure, not attainment | Opening the app, an imported file, an unrelated page view |
| Understood | A policy-qualified explanation check with inspected task/rubric, recorded result and assistance context; state what was demonstrated in that check | Reading, bookmarks, one aggregate score, any evidence row |
| Practised | A qualifying application task and result, with help/conditions disclosed; distinguish attempted from successful practice | Merely opening/running a notebook, a code cell without a check |
| Demonstrated | A qualifying independent application opportunity under explicitly defined conditions, result and provenance | Zero recorded hints, high confidence, full credit, transfer task type or elapsed time |

These are separate evidence facets, not a forced ladder: practice does not establish
understanding of every concept, and a later failure does not erase prior dated work.
Keep Recall and its scheduling separate. Do not add percentages as substitutes.
Unknown/missing evidence means not established, not learner failure.

## Decision required before new attainment labels

Record a versioned policy through the existing ADR process before changing the
kernel or activating new attainment labels. Resolve all of the following together:

1. Task eligibility and rubric requirements per facet, including deterministic versus
   model-checked results. A model judgement must remain identifiable and challengeable.
2. Success criteria, repeated evidence and recency rules. Do not invent a numeric
   threshold or treat the current kernel constants as validation for these labels.
3. Assistance conditions and observation limits. App-observed help, full-solution
   exposure, revised work and learner-reported external help are different facts.
   Absence of an event is not proof of no help. Self-report is labelled as such.
4. Meaning of an independent opportunity and how its conditions are established.
   Do not imply surveillance or require tracking other apps. If independence cannot
   be established, retain an explicit limitation instead of promoting the label.
5. Disputed/corrected evidence, invalidated source versions and policy changes:
   retain original records, explain exclusions and permit recomputation/audit.
6. Whether this is display-only or changes gating/scheduling. Default implementation
   scope is display-only; changing learning decisions is a separate explicit decision.

Do not silently adopt this proposal as an accepted ADR. Existing owner-approved
learning policies and manual-only ADR conventions remain in force.

## Bounded implementation sequence after the decision

**P-E1: provenance foundation.** Add only the missing accepted metadata, with nullable
legacy values and versioned policy identity. Bind provenance to exact attempt/content
and learner; capture known assistance facts without deriving missing facts. Preserve
transactional grading/retry boundaries and backup/restore. No historical backfill of
independence or successful exposure from score/hint defaults.

**P-E2: deterministic read model.** Derive display facets from immutable eligible
records under the accepted policy. Return label, date, supporting record IDs, limitations
and policy version. Keep database reads side-effect free and learner scoped. Do not
call models to classify attainment or mutate competency/FSRS on page load.

**P-E3: design-system presentation.** Adopt the page8 word+glyph+semantic-token pattern
in the existing Progress page. Each claim links to its task, result and conditions.
Show unknown evidence plainly. Keep the existing Why disclosure, history pagination,
corrected/disputed records and Next useful evidence action. Avoid inventing a new
recommendation engine or silently switching the selected lesson.

**P-E4: acceptance.** Verify before enabling the display, with the same cases in
backend fixtures and browser flows where applicable:

- Empty history; exposure only; failed, partial and successful checks.
- Zero hints plus full-solution exposure; missing help history; reported external help.
- Immediate revisions, replays/duplicate requests and later genuinely new tasks.
- Missing/deleted/foreign attempt or saved-answer references; changed content versions.
- Disputed/corrected evidence; different policy versions; export/restore and legacy nulls.
- Stable dates/counts/pagination, no page-load writes and unchanged existing gating/FSRS.
- Light/dark,320px, actual zoom, keyboard, word+shape meaning without colour, screen-reader
  reading order and human ability to explain why a label appears.

Code and pedagogy reviews are required for each implemented slice. Human acceptance
is separate from automated accessibility checks. No new dependency is justified.

## Current stopping boundary

This contract identifies the missing semantics; it does not certify current evidence,
introduce new states, or authorize changing accepted kernel thresholds. Continue other
independent design/reliability tasks while the policy remains unresolved. The existing
Progress evidence view remains usable and accurate within its documented limits.


## Concrete decision proposal — 2026-10-12, not accepted

Recommended first scope: a display-only evidence policy. Keep current kernel,
prerequisites and FSRS untouched. Display dated, task-specific claims rather than
permanent skill badges or a forced ladder. The following resolves the proposed
policy choices for owner review; it does not authorize implementation or an ADR.

| Decision | Proposed rule |
| --- | --- |
| Exposure | Record an explicit learner “I read this explanation” action tied to exact concept/content version; show it as learner-reported exposure. Page opening alone never qualifies. |
| Understanding check | Only a task explicitly designated as an explanation check with a versioned, reviewed rubric can qualify. Every required criterion must pass; disclose deterministic/model/human checking. State “Explanation check passed” with date and task, not an unqualified claim that the concept is understood. |
| Practice | Distinguish “Application attempted” from “Application check passed.” A designated application task, exact work and recorded check are required; merely running code is insufficient. |
| Repetition and recency | Keep dated results visible; no expiry or fixed number of repetitions establishes attainment. Immediate revisions remain marked practice and never become additional independent demonstrations. |
| Assistance | Show observed hints, full-solution exposure, revision lineage and voluntary external-help self-report separately. Legacy/missing observations remain unknown. No cross-app monitoring. |
| Independence | Leave “Independent application not verified” in place. A learner's no-help report may be displayed as self-report, but does not activate Demonstrated. A later independently reviewed opportunity policy is required for that claim. |
| Disputes and versions | Preserve original outcomes. Mark disputed/corrected results and incompatible content versions; exclude them from current qualified summaries until explicitly resolved. Record policy version and exclusion reason; no silent retroactive rewriting. |
| Learning decisions | Display-only. No score-threshold changes, gating changes, scheduling changes or model classification on page load. |

This deliberately refines the design's Understood/Practised wording into observable
check results until stronger evidence can support broader claims. That wording
choice needs owner agreement because the complete design system is authoritative.
The existing factual Progress page remains the alternative while this proposal is
unresolved. P-E1–P-E4 stay open; do not mark this draft as an accepted policy.


### Owner decision recorded — 2026-10-12
Owner selected “Use task-specific evidence labels” in response to the concrete
choice between that first implementation and retaining the current display.
Approved: dated Explanation check passed / Application attempted or passed labels,
help disclosed, independence unverified, display-only with no grading/scheduling
change. This supersedes the unresolved wording choice above. It does not authorize
inventing eligibility from aggregate scores or retroactively certifying old work.

Current implementation inspection confirms ProgressEvidence has only dimension,
score, grader, date, attempt reference and hint count. It does not carry a versioned
eligible task/rubric or complete assistance context. Therefore first implement the
provenance foundation and unknown fallback, not a frontend score-to-label mapping.
Do not treat one full-credit evidence row as automatically qualifying under the new
policy. Remaining detailed lifecycle/exposure rules above retain their proposal
status until incorporated through the existing versioned-policy process.
