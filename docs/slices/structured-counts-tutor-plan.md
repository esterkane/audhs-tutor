# Explicit group-count evidence for Study Tutor

Status: proposed implementation contract, 2026-10-11. No runtime change or quality pass.

## Concrete problem and inspected implementation

The retention-consistency evaluation reproduces an explanation inconsistent with supplied
counts. The rejected prompt candidate does not resolve it; see local-tutor-latency.md.
`frontend/src/features/programs/GroupCounts.tsx` already validates 2–8 groups and computes
retention and representation locally. It only receives a storage key, and explicitly says
counts are not sent to the tutor. `StudyTutor.tsx` embeds it, but there is no structured
count field in `backend/app/schemas/playground.py`. Existing workspace arithmetic checks
inspect literal equalities in an answer; they do not establish group-count evidence.

This is a missing evidence contract, not proof that attaching numbers will fix model reasoning.
Do not infer authoritative counts from prose, automatically execute notebooks, or replace
incorrect generated sentences with sample-specific substitutions.

## Smallest coherent implementation

1. Add an optional typed comparison input: unique trimmed group labels and bounded whole
   before/after counts, preserving existing removal-only assumptions. Reject booleans,
   fractional/negative counts, duplicate labels, after greater than before and oversized inputs.
   Validate on the server; never trust client-calculated percentages.
2. Compute removed counts, exact retention fractions and before/after representation using
   deterministic code. Zero denominators remain undefined. Label observations as conditional
   on user-entered data and the supplied group universe; do not claim dataset verification,
   causation, accuracy or fairness. Preserve exact fractions alongside rounded display values.
3. Offer explicit attachment of the compared snapshot in Study Tutor. Comparing alone must
   not call the model or attach data. Show the attached groups and allow removal. Editing counts
   invalidates the attachment until explicitly compared and attached again. Capture immutable
   evidence with the submitted request; subsequent edits cannot change that request's meaning.
4. Pass validated input and deterministic observations as untrusted evidence through the existing
   workspace path. Display the local calculation separately from fallible generated explanation.
   Preserve hint intent: no newly disclosed complete solution when asking only for a hint.
5. Bind evidence to request identity, saved-answer reuse and history provenance. Omit the new
   optional field when absent so old serialized payloads/fingerprints remain compatible.
   Changed counts must not reuse an answer grounded in older counts. Audit every exact-reuse
   and semantic-history eligibility path before enabling the feature.

Likely changes: GroupCounts and StudyTutor components/tests; playground request schema and
generated client types; workspace evidence/orchestration and their tests. Inspect existing
saved-answer eligibility and request fingerprint consumers before deciding the exact backend
file set. No new library, model, provider, database table or learning-kernel change is proposed.

## Acceptance, in order

- Deterministic cases: renamed/reordered groups, unequal totals, zero group/overall totals,
  unchanged counts, all removed, bounds and invalid input. A100→90/B50→30 must give removed
  10/20, retention90%/60%, and B share1/3→1/4; do not hard-code these groups.
- Compatibility: absent evidence retains existing fingerprints; changed evidence prevents exact
  reuse; uncertain retries preserve the original snapshot and do not issue a second generation.
- UI: explicit attachment/removal, edit invalidation, step switch, delayed response, reload and
  storage failure. Preserve the learner's question and draft; expose stale/unsaved state honestly.
- Browser sandbox: desktop/narrow, keyboard attachment and removal, visible calculation,
  no overflow, no model request on Compare. Inspect screenshots and rerun existing tutor recovery.
- Run focused unit/integration tests, lint/types/build, and bounded code/pedagogy reviews.
- Only then run one local retention evaluation with the same manual semantic criteria. Report
  any continuing contradictory explanation as unresolved; deterministic correctness is not a
  model-quality pass or a performance improvement. Do not begin another prompt experiment loop.

Before implementation, render the existing comparison flow in the disposable sandbox and record
the learner-visible starting point. Current investigation inspected code only. This contract leaves
mastery, grading, scheduling, course activation and saved learning evidence unchanged.

## Internal foundation verified — 2026-10-11

Added `backend/app/kernel/group_counts.py`: strict, immutable input snapshots and pure exact
fraction observations, with removal-only validation and undefined zero-denominator results.
No endpoint, prompt, client type or UI consumes it yet. The existing comparison UI remains unchanged.

29 focused tests pass, including coercion rejection, bounds, trimmed duplicate labels, row reorder,
zero totals, maximum counts and immutable input. Focused Ruff/format and mypy pass; bounded code
and pedagogy review found no actionable issue. Existing 390/1280 browser comparison journeys
passed before implementation (keyboard Compare, edit invalidation, reload and no model calls).
No new rendered UI or visual-acceptance claim; no model experiment.

Boundary investigation: `db/answer_memory.py:candidates` compares a fixed list of work fields,
whereas `exact_saved` uses the serialized request. Adding an API field alone would leave semantic
history eligible across different counts. Next add the optional input with compatible serialization
and update candidate eligibility, request replay and saved context before exposing attachment.
Old replies remain history, not verified arithmetic. No speed or model-quality improvement claimed.
