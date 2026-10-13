# Saved answers to lesson drafts — G5 implementation boundary

Status: implementation plan, not a publication or permissions approval.

## Concrete gap
`TutorAnswer` retains an answer snapshot and generation metadata; the read-only
`answer_visual_binding` resolver checks answer ancestry and source versions.
`CurriculumDraft` stores editable payload JSON, but `curriculum.publish_draft`
projects only selected fields into LearningObject and Assessment. Arbitrary draft
metadata alone therefore cannot guarantee durable answer lineage after activation.
Current publication also creates shared curriculum objects and assessments. That is
not a sufficient access boundary for learner-private answer-derived content: a private
provenance link does not make a shared learning object private.
The synthetic leakage lesson is a content pilot, not an answer-promotion implementation.

## Required behaviour
An explicit “Create lesson draft” action on a saved Ask answer should prepare an
inactive, learner-owned draft. The owner supplies or reviews the objective,
prerequisites, worked example, practice question and complete rubric. No reading,
editing or acceptance of an answer automatically creates learning evidence.

Capture exact answer identity/content hash, ancestry and source-version hashes on
the server. A caller must not assign ownership or supply trusted provenance.
Unknown/incomplete lineage remains visible and restricted; editing generated text
must not make it eligible for hosted transmission or public export. Model-authored
content is not automatically owner-authored content. All drafting remains local.

A repeated command with the same key/body returns the same draft. Changed body or
answer/source identity conflicts. An interrupted model request must not silently
regenerate, and edits made after sending must survive an uncertain result.
Activation remains a distinct explicit action. Published objects must retain a
stable link to the reviewed originating draft/version and provenance record.
Task/rubric qualification remains the separate exact-content review contract.

## Implementation order
1. Define and test a server-owned promotion binding and immutable lineage record,
   including backup, restore and learner wipe. Reuse existing answer resolution
   where semantics match; do not treat a visual presentation review as lesson approval.
2. Resolve publication ownership before promoting private answers: learner-private
   derived content and its provenance must remain inaccessible to other learner IDs
   through planning, retrieval, assessment selection and direct reads. Existing shared
   publication must reject private promotion bindings until this is implemented.
   Document the schema/access design before coding; localhost single-owner deployment
   is not evidence of cross-learner isolation.
3. Add idempotent inactive-draft creation using the current curriculum validator.
   Start with explicit structured fields rather than automatic model generation.
   Extend publication to retain the binding; do not rely on payload extra fields.
4. Add an Ask action with a preview of objective, content and source restrictions,
   then open the existing draft editor. Preserve cancellation, retry and local edits.
5. Add explicit optional local generation only after deterministic creation works.
   Evaluate factual fidelity and educational usefulness separately from schema validity.
6. Add objective/task replacement coverage, preserving previous evidence and source
   dependencies. Removal requires a separate owner decision; never delete sources
   because an answer or lesson was generated.

## Acceptance evidence
Use cross-learner publication/read/planning/retrieval isolation tests, owned/foreign answers, changed and missing sources, incomplete ancestry, edited
criteria, duplicate commands and lost responses. Verify no new assessments or
learning evidence before activation, exact binding after publication, no ownership
upgrade and no hosted call. Check desktop/narrow keyboard review and recovery.
Tests do not establish transfer effectiveness; actual learner checks remain separate.

## Current pilot
The approved fit/transform transfer lesson is an inactive local draft. Browser
inspection confirms the explanation, arithmetic, question and full rubric render;
its missing-source warning is visible. Explicit activation is pending. This pilot
must not be described as end-to-end G5 completion or removal of course dependencies.

## Review
Architecture review confirmed the projection gap and identified shared publication
as a major missing boundary; the staged plan now requires ownership/access resolution
and refusal of private promotion until that boundary is implemented. No runtime change.
