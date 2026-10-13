# Authored visual lifecycle — decision proposal

Date: 2026-10-13. Status: Accepted by the owner on 2026-10-13.
Implementation is staged; acceptance itself did not activate migrations or endpoints.
Implements the prerequisite in slices/visual-learning-binding.md and G4 of
CROSS-TOPIC-CONTENT-WORKSPACE.md. Retains the learning kernel and existing renderers.

## Recommended decision

Store learner-owned visual documents separately from disposable Representation cache.
A document has immutable numbered content versions. Editing creates a new version;
review receipts bind to the exact version/hash and do not transfer to later edits.
Archive hides a document reversibly; no automatic expiry or permanent purge in the
first release. Local storage never confers hosted/public-export permission.

### What each version explains

Use a discriminated target, never invent a LearningObject to satisfy a schema:

- **Lesson:** exact existing VisualBinding (object/version/skill/goal/criterion indices
  and text/source hashes), resolved against stored records. This does not alter the
  objective, grade or schedule.
- **Ask answer:** server-resolved owned answer ID, exact question and answer hashes,
  original date/model/prompt identity and complete source/ancestry snapshot. An
  optional plain-language learning purpose is author intent, not a reviewed objective.
  No criteria, skill or mastery claims are fabricated. A source-free answer can have
  an explicitly ungrounded visual; missing lineage stays unknown, not owner-authored.

The existing lesson-only relationship wire schema remains unchanged. Introduce a
new explicitly versioned envelope for answer-target visuals; share bounded node/edge
validation internally. Never reinterpret old lesson payloads as answer bindings.
The rendered diagram and text equivalent display target and grounding/review status.

### Storage and acceptance

Proposed document record: learner ID, ID, title, latest-version pointer, archived flag.
Proposed version record: document/learner/version IDs, prior version, validated spec,
content hash, target/provenance snapshot, creation time and model/prompt origin when
applicable. Content fields are immutable; no generic patch of historical JSON.
Proposed review record: owner, version/hash, exact target snapshot, timestamp and
review outcome/notes. Schema validity, owner review and model review are distinct.

Draft creation and review use learner-scoped request identities/fingerprints; retries
return the original receipt, changed bodies conflict. Revalidate target/source hashes
inside the same write transaction as acceptance. Edits and changed/missing references
prevent a new current acceptance; historical versions remain readable with warnings.
An accepted visual is reviewed presentation, not certified truth or learning evidence.
Explicit user display/render is separate from creating or accepting content.
No automatic model generation on load, retry, failed rendering or archived recovery.

### Backup, export and retention

- Full **private** backup includes visual documents, all versions, review records and
  source provenance. Restore preserves IDs/hashes/statuses, then reports missing or
  changed referenced records rather than relinking to the newest source.
- Default learner backup follows existing ADR-0012 treatment of derived learner
  artifacts: include visual specs/review history, omit raw corpus passage snapshots
  that were included for generation. Retain identifiers/hashes/origin restrictions.
  Restore must distinguish missing grounding material from a fully restored source.
  Manifest warns that derived visual labels/text may quote third-party material;
  learner backup remains private, not a public content export.
- Neither backup is a public export. Existing owner-only transmission/public-export
  rules remain unchanged; mixed/unknown/source-derived visuals stay local.
- Cache invalidation deletes rendered artifacts only. Archiving is reversible and
  preserves versions, reviews and target provenance. Permanent purge and its impact
  on linked history require a separate explicit design/action; not in this release.
- Existing explicit learner wipe still removes that learner's visual documents,
  versions, reviews and private snapshots in dependency order. Archive-only refers
  to individual document controls, not an exception to learner wipe. Never delete
  shared corpus records as a consequence of wiping one learner.

## Implementation order after acceptance

1. Typed answer-binding envelope and owner-scoped stored-record validation, including
   complete lineage and absent/changed-source statuses; no generated executable code.
2. Migration and transactional version/review repository with idempotency, ownership,
   rollback/concurrency and archive/restore tests on disposable SQLite databases.
   Add private backup/restore, scoped learner-wipe and complete table-inventory
   tests before exposing a write endpoint.
3. Bounded authenticated API: read/list, explicit draft/version save, review, archive
   and restore. Enforce payload limits before parsing; deny cross-owner IDs; no
   source text in logs. Do not treat a read-validator result as a durable review.
4. Inline Ask visual draft/review with existing relationship renderer and text
   equivalent. Explicit local generation, cancel/recovery, source access, keyboard,
   narrow/zoom/reduced-motion and failed-render fallback. No automatic retry inference.
5. Add one reviewed worked prediction and optional understanding question through
   existing assessment contracts; separate visual preference from learning evidence.

## Alternatives and risks

Reusing Representation is smaller but cache deletion would destroy authored history.
Saving anonymous graph JSON in answer metadata avoids a migration but lacks version,
review, backup and retry boundaries. Both are rejected in this recommendation.
Immutable history increases storage; bounded payloads and reversible archive are the
initial limits. Owner review cannot certify factual correctness. Broad semantic
quality and assistive-technology acceptance remain independent gates.

## Owner acceptance

The owner explicitly accepted the recommended lifecycle, including private learner-backup
treatment of derived specs and reversible archive without automatic deletion. This authorizes implementing
the staged migration/API; it does not approve any generated visual, publish curriculum,
change provider routing or authorize public release of content.

## Proposal review

Code/provenance review identified the need to preserve explicit learner-wipe semantics;
that requirement and scoped-wipe/table-inventory tests are included above. No runtime
change or acceptance is implied by this documentation review.
Re-review confirmed the wipe finding resolved, with no remaining blockers/majors.
Owner acceptance was subsequently received: “Accept the proposed lifecycle”.
The owner authorizes staged storage/API implementation under this contract; the reviewer
did not supply that authorization.


## Implementation status — 2026-10-13

Binding, immutable storage, private backup/wipe, transactional document commands,
read/version/review APIs and exact Ask target preview are implemented. See
slices/authored-visual-storage.md, slices/authored-visual-commands.md,
slices/authored-visual-history.md and slices/ask-visual-generation.md (under docs/).
Durable generation requests, explicit local generation start/status/stop and the
inline Ask visual panel are implemented. See slices/ask-visual-worker.md,
slices/visual-generation-api.md and slices/ask-visual-ui.md. Exact-version review/edit/
archive UI and semantic-quality acceptance remain open; the two-case local trial
found meaningful errors (slices/ask-visual-fidelity.md). Existing local single-owner access is not multi-user authentication.
No generated content approval, public-export permission or learning evidence follows
from completing these implementation foundations.
