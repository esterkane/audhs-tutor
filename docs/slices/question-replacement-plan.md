# Reviewed question correction and replacement — implementation contract

Status: planned, not implemented. Continues R5 after explicit practice controls. This document records architectural gaps found in current code before expanding runtime scope.

## Current evidence

- `backend/app/db/models.py`: Assessment is shared; QuestionState and QuestionTransition are learner-scoped. No replacement relationship exists. A missing state row means active.
- `backend/app/kernel/question_state.py`: selectors exclude nonactive rows for the current learner; transition supports suspend/restore with revision checks and repeat-safe receipts. Merely inserting a new Assessment makes it eligible for other learners unless selection rules change.
- `backend/app/kernel/question_feedback.py`: reports retain immutable snapshots and withdrawal; summary returns the latest 100 raw records, with preference suggestions. This is not a correction queue or a resolution ledger.
- `backend/app/api/exercises.py`: code exercises retain a concrete linked assessment ID and question text. Replacing only the linked assessment does not redirect the exercise. Historical snapshots must remain immutable.
- Existing UI controls only change eligibility. Reporting alone changes neither eligibility nor competency.

## Invariants

A correction is a proposal until explicitly published. Preserve the old assessment, rubric, attempts, feedback snapshots, execution receipts and review history. Do not transfer old mastery or FSRS state to a new question or automatically regrade past answers. Do not publish actual learner material during implementation; use isolated synthetic data.

Long-lived drafts also retain a stable server-private content fingerprint, independent of process-bound public submission tokens; restarting must not silently rebase a proposal. Drafts retain original assessment/content token, learner state revision, source IDs/versions, proposed typed payload and rationale. Editing or withdrawing a report is not publication. Source absence/conflict must be explicit; retrieval text is untrusted evidence, not an instruction. Proposal generation is optional and local-first; manual correction works without a model.

Publication must validate source/content/state/draft versions within a transaction, create a new identity, supersede the old identity for the intended learner, record lineage and an immutable receipt, and resolve the proposal atomically. Same request/body returns the original outcome; reused ID/different body and concurrent stale publication conflict. A timeout is an uncertain result, not permission to generate a new request ID. Replacement resolution must never redirect an existing submission or recovery receipt: pending old work conflicts safely, while completed outcomes replay against their original identity.

## Ordered implementation slices

1. **Typed correction inbox, read-only first.** Paginated learner-owned actionable reports, deterministic ordering, original snapshot versus current content, withdrawn/resolved status and unavailable-content handling. Preserve the existing feedback/preference API. Distinguish assessment reports from unpublished draft reports; do not silently combine identities. Add resolution lifecycle only with explicit commands. Tests: learner isolation, pagination, withdrawal, repeated reports, deleted/unavailable targets and no mastery writes.
2. **Versioned proposal draft and preview.** Reuse public typed question schemas, retaining full answer/rubric only in the explicit authoring context. Start from the original content rather than a blank form. Preview exact before/after wording, answer/rubric changes, source provenance, new identity, affected pending review count, retained history and linked consumers. Dirty edits survive conflicts. No publish button until ownership/lineage below is enforced end-to-end.
3. **Replacement ownership and resolution foundation.** Add explicit learner-owned replacement lineage and ensure replacement-only assessments cannot enter other learners' selection/generation caches. Inventory ordinary/challenge/listening/code/direct assessment/review/hint/solution paths. Resolve forward references for future practice while historical reads keep old IDs. Code-linked questions require a resolved identity and matching text/token; never mutate the original exercise snapshot to redirect history. Verify chains, cycles, same-skill/kind compatibility, stale tokens and unavailable replacements. Schema/index/backup/export/wipe coverage required. Resolve the storage design in an ADR before schema work; this plan is not ADR acceptance.
4. **Atomic explicit publication.** Implement the transaction/receipt contract above, show a final preview tied to its revisions, and recover a lost response by receipt lookup. Old review cards remain historically intact and excluded; the replacement receives review scheduling only through normal learning evidence. Reversal needs an explicit previewed policy, not the existing suspended-to-active endpoint applied to superseded content. Test concurrent publish, rollback at every write boundary, exact repeat, altered repeat, post-commit response loss and another learner's unchanged behavior.
5. **Integrated sandbox acceptance.** Report, inspect, edit, preview and publish; old queued question cannot be newly answered/reviewed, historical feedback remains readable, replacement is reached in every supported future-practice surface and no duplicate evidence is recorded. Desktop/narrow, keyboard, focus, Back/reload, failed reads and slow writes; code and pedagogy review. State unsupported kinds explicitly rather than claiming universal replacement.

## Next bounded task

Read-only inbox API/UI is implemented and verified in question-correction-inbox.md. ADR-0019 and internal durable draft commands are prepared/implemented. Next add kind-specific validation and source-version snapshots before exposing proposal editing/preview. Keep resolution explicit and do not introduce publication until learner-scoped visibility and original-receipt identity are enforced.

## Acceptance still open

Slice 1 read-only discovery is now implemented (see question-correction-inbox.md); its resolution lifecycle and slices 2–5 remain unfinished. The prior controls prove suspension/restoration only. Human comprehension, broader accessibility, real material provenance and approved replacement policy remain separate gates. No runtime changes or new test claims accompany this planning document; its evidence is targeted inspection of the listed implementation.

Bounded architecture review confirmed the listed code facts and added stable draft fingerprint and original-receipt identity requirements.

Storage/command proposal: [ADR-0019](../adr/0019-learner-owned-question-corrections.md) specifies explicit assessment ownership, durable proposal fingerprints, repeat-safe draft commands and kind-specific adapters. Internal draft storage is implemented in correction-draft-foundation.md; replacement ownership and publication remain proposed and disabled.

Internal core/challenge validation and source-identity capture are implemented in correction-validation-sources.md. Next expose owned draft commands/recovery and a typed editor; code execution review, listening revalidation and publication remain open.
