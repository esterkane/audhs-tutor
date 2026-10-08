# 0019 — Learner-owned question corrections

Date: 2026-10-08
Status: Proposed implementation contract; no migration or runtime adoption yet

## Context

R5 requires reviewable corrections with immutable history. Assessment rows are currently shared and active for a learner unless QuestionState says otherwise. Inserting a replacement without ownership would expose it to other learners. Catalogued code exercises retain fixed check-assessment references. Feedback snapshots retain payloads but not rubric versions or a durable draft-question index. Public assessment tokens expire with the process. Existing AssessmentIn deliberately allows extra fields and does not enforce kind-specific grading validity.

## Proposed decision

Keep the current deterministic kernel, SQLite and provider boundaries. Add a nullable `owner_learner_id` on Assessment: null denotes existing shared content; non-null denotes private correction content. Use a restrictive learner foreign key, never SET NULL on deletion. All future selection/reuse and direct question reads must enforce shared-or-owned visibility independently of eligibility. Historical own receipts retain their original assessment identity. Ownership is not merely a QuestionState row: absence of a state row cannot make private content public.

Add learner-owned correction proposals and immutable publication receipts, plus explicit replacement lineage. Do not alter existing Assessment or rubric payloads during correction. Publication creates new owned identities and supersedes the original for that learner in the same transaction. A replacement's rubric is a new immutable row when needed. No old attempt, card, source association or rubric is retargeted. No old mastery or FSRS schedule transfers; normal future evidence creates any new review scheduling.

For future practice only, a resolver follows the learner's lineage to its terminal replacement. It rejects cycles, incompatible skill/kind changes and inaccessible/deleted targets. Apply the same resolver to ordinary selection, saved challenges, listening tasks, code/check references and direct practice entry. Selection and canonical generation must not recreate an excluded predecessor. Existing submissions, recovery receipts and historical reads NEVER follow this resolver. Pending old work conflicts safely; completed results replay against the original identity.

## Proposal record and commands

Store: proposal ID/learner, optional originating report ID, original assessment ID, draft revision, status, immutable original full snapshot including rubric, server-private stable content fingerprint, expected question-state revision, source identity/version evidence, kind-specific candidate payload/rubric, rationale and timestamps. Stable fingerprints remain server-private; public submission tokens are neither durable draft identity nor exposed answer hashes. Source content identities are checked separately because assessment fingerprints do not snapshot source text.

Commands are explicit create, save, discard and publish. Each write has a request UUID and an immutable request/result receipt within the same transaction. Save checks draft revision; it never rebases onto current content automatically. A stale original/source/state blocks preview publication while preserving candidate edits. A successful create/save is not publication and does not resolve feedback. The browser retains dirty edits on 409; a response timeout offers lookup/retry of the identical command, not a new UUID. Receipts are learner-owned and validate request equality before replay.

A read-only preview describes before/after wording, answer/rubric changes, original sources and their current availability, affected current review count, new identity and retained history. Publication rechecks all identities and revisions under the write lock; the preview is not a substitute for transaction validation. Mark the proposal published and associate its report resolution only on successful publication. Standalone dismiss/resolve is a later explicit action, not inferred from a positive rating or suspension.

## Typed content and teaching invariants

Adapters preserve unedited metadata and source associations from the server snapshot. Clients cannot choose ownership, skill, original identity, provenance or an arbitrary rubric ID. Reuse established kind shapes, but validate fields before saving a candidate:

- MCQ: nonempty wording, bounded distinct options, integer answer index in range and explanation. Changing options requires deliberate correct-answer selection.
- Cloze: nonempty displayed text and nonempty bounded accepted answers; retain the current grader's normalization contract.
- Explain-back/transfer: prompt and nonempty criterion structure consistent with the existing rubric grader; distinguish an example answer from an assessable criterion.
- Challenges: preserve mode, validate prompt/hidden reference/criteria through the current challenge contract; hidden reference is visible only in explicit authoring.
- Listening: preserve clip/source/task association; corrected wording must remain grounded in the identified segment.
- Code: retain execution policy/runtime/source/check associations; corrections to executable checks require their own sandbox verification. Never execute candidate code during save/preview.

Unsupported adapters must return an explicit unsupported-kind result and retain reports/drafts; do not pretend a generic JSON save proves pedagogical validity. Each adapter needs fixtures from real schema shapes and negative cases before enabling its editor. Validation is not proof of correctness; reviewed source comparison remains necessary. Authoring reveals reference answers intentionally and must not create mastery evidence.

## Migration, portability and release gates

Add ownership with existing rows remaining shared. Add indexes for owner, original identity and learner proposal status; constrain lineage and receipt uniqueness in the database. Wipe/export/backup must explicitly include private assessments and dependent rubrics/lineage, since generic LearnerScoped discovery does not cover `owner_learner_id`. Deleting an owner must never make formerly private content shared. Test an actual export/restore/wipe, not just table presence.

No publication endpoint is enabled until all current selection/direct-read paths enforce ownership. Before release: two learners; excluded/retired/replaced chains; linked code/check text and token agreement; same-request replay/different-body conflict; concurrent publish; rollback at each write boundary; restart with unchanged draft; changed original/rubric/source; lost response; completed historical replay; and UI preview/dirty-edit recovery with keyboard/narrow layouts. Tests use synthetic sandbox data only.

## Alternatives

- Mutating original content would change the meaning of history: rejected.
- Globally replacing shared content would override another learner: rejected.
- Encoding ownership only in JSON or suspension rows would allow missed filters/default-active leakage: rejected.
- A second assessment storage engine would duplicate grading/review integrations: unnecessary at this stage.

## Adoption boundary

This is a proposed contract, not a claim of implementation or an accepted change to grading policy. The next implementation slice is durable proposal create/read/save with revision/receipt tests and export/wipe coverage, followed by a typed preview/editor. Publication remains disabled until the ownership/resolver matrix is proven. Existing local-first routing and no-automatic-curriculum-publication policy remain unchanged.

Review: bounded independent architecture review found no major omitted invariant or contradiction with the inspected implementation. This review does not constitute runtime acceptance.
