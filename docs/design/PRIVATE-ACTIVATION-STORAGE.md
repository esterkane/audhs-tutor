# Private activation storage and command contract

Implementation specification for the remaining stage of PRIVATE-LESSON-ACTIVATION.md.
This does not enable activation, qualify an assessment, approve a lesson, or change source rights.

## Verified existing boundaries

LessonPromotion freezes learner/draft/answer identity, request fingerprint, binding and source
check state; LessonPromotionSnapshot separately holds raw origin history. CurriculumDraft remains
editable with increasing versions until published/rejected. Shared publish explicitly rejects
promotion-linked drafts. Skill/assessment ownership is immutable; inherited content and edges are
guarded. Current model transports are local-only and private lesson text must not enter the shared
corpus index, whose filters have no learner ownership dimension.

## Storage layout

Use a new LessonActivation header with learner_id, promotion_id, request_key, command fingerprint,
exact draft_version, canonical payload_sha256, payload_json (edited teaching content), binding_json
and created_at. promotion_id is globally unique: one promotion creates one activation. The pair
(learner_id, request_key) is unique. A composite FK to LessonPromotion(learner_id,id) prevents
foreign origins. Draft identity follows the immutable promotion; do not duplicate a mutable draft
relationship. Store the accepted request fingerprint separately from the payload hash.

Use four explicit link tables for created skills, learning objects, assessments and edges. Each
has learner_id, activation_id and the concrete entity FK. An entity belongs to at most one
activation via a unique entity ID; activation_id/learner_id is a composite FK to the header.
Prefer these typed links over unvalidated entity IDs in JSON. Multiple skills/objects/assessments
remain representable: the generic draft editor must not be silently reduced to one question.

Membership guards require on insertion:
- skill links reference a skill owned by the same learner;
- object links reference an object whose skill is linked to this activation;
- assessment links reference an assessment owned by the learner with a skill linked to this activation;
- edge links target a skill linked to this activation; the existing edge guard enforces the prerequisite owner.

These are persistent membership invariants, not insertion-only checks. Add guards on
LearningObject.skill_id and Assessment.skill_id updates: an activation-linked entity may move
only to another skill linked to the same activation (ordinary same-owner moves outside that
activation must fail). On SkillEdge endpoint updates, require its target to remain linked to the
same activation; the existing owner guard continues to constrain its source. A shared or
same-owner prerequisite need not itself have been created by this activation.

Reject deletion of an activation skill link while any linked object, assessment or edge target
still depends on that membership. Wipe must delete dependent activation links before skill
links, then headers, before deleting curriculum rows. Do not rely on insertion order, independent
entity foreign keys, or immutable link rows to enforce these cross-table relationships. Content
without activation links retains its existing same-owner reparenting behavior.

Insert the header, then skill links, then dependent links, inside the one activation transaction.
All headers/links reject UPDATE. Normal deletion remains available only through existing scoped
lifecycle/wipe services; foreign keys preserve referenced history. Frozen payload is creation
history, not a claim that every mutable curriculum field still equals its original value.
Future editing must retain this distinction and use versioned objects, not overwrite the receipt.
Do not add these guards to constants imported by already-shipped migrations: use a separate DDL
collection so replaying old migrations does not try to create triggers for tables not yet present.

## Activation command

No model, retrieval, index or network work inside the transaction. The explicit request includes
promotion identity, expected draft version, exact payload hash and durable request identity.

1. Parse and bound input; resolve the active learner from the server, never the payload.
2. BEGIN IMMEDIATE. Look up learner/request identity first. An identical retry returns the original
   receipt even if the draft has changed since; a different command with that key conflicts.
3. Resolve the owned promotion and its draft. Refuse missing/foreign, non-draft, stale version or
   payload hash, and an already-activated promotion under a different key. Keep source history
   separate from edited fields; do not trust editable origin metadata for authorization.
4. Revalidate the stored lesson binding and current source-check state. A changed/missing origin
   returns a conflict without discarding the draft. Initial implementation must not silently rebase
   source history. A later explicit rebase/review flow requires its own contract; copying retained
   edits into a freshly reviewed draft remains possible. This is conservative identity checking,
   not factual verification or permission approval.
5. Validate the complete payload, duplicate mappings and prerequisite graph. Resolve prerequisites
   to shared or same-owner nodes only. Keep the shared validator's current shared-only behavior;
   introduce an explicit private validation context rather than broadening shared publication.
6. Generate fresh IDs/slugs for private nodes; map draft slugs internally. Never upsert global slugs,
   mutate shared nodes, infer a shared area, or overwrite source metadata. Create versioned objects,
   private assessments/rubrics and valid edges; add every typed activation link.
7. Store the immutable canonical payload/binding and receipt; mark the exact draft published and
   increment its version in the same transaction. Failure anywhere rolls back every write.

Do not create AssessmentTaskReview, AssessmentAttempt, CompetencyEvidence or MemoryState rows.
Activation and its receipt are not learning evidence. No new learning-event verb is required for
storage; if UI analytics are added, define their event contract separately.

## Recovery, export and migration

The header and links are learner-scoped and must participate in export and dependency-ordered
wipe before their referenced promotion/curriculum rows. Learner backups retain edited payload and
activation links; raw origin snapshots remain full-private-only. Backup schema validation must
require immutable guards only when their tables exist, accept earlier revisions for migration,
and validate actual owner/membership relationships after restore (triggers alone do not validate
preexisting rows). Reject downgrade with activation history before dropping anything.

Use a disposable populated migration copy before live apply. Test two learners plus shared
prerequisites, multiple created entities, malformed memberships, update refusal, foreign receipt
reads, same-owner reparenting within/outside activation membership, skill-link deletion with
dependents, permitted unlinked-content edits, restore after permitted edits, duplicate/concurrent requests, different-key duplicate activation, exact retry after lost
response, stale draft/source identity, late write failure, learner/full backup and scoped wipe.
A full-schema reflective fixture must remain meaningful; do not weaken ownership constraints just
to accommodate generated fixture rows.

## Delivery sequence

1. Header/link schema, guards, backup/wipe and migration tests. Producer remains disabled.
2. Atomic activation repository and read-only receipt lookup with concurrency/failure tests.
3. Explicit preview/activation/recovery UI, source warnings, keyboard/narrow/browser verification.

The synthetic pilot is already activated under its separate owner decision. Do not activate it
again, and do not interpret that decision as authorization to activate any other saved draft.

## Architecture review disposition

The first bounded review found that insertion-only guards permitted later same-owner reparenting
to violate membership, causing restore to reject an otherwise writable database. The contract
now explicitly preserves membership on entity updates and skill-link deletion, while retaining
ordinary edits and unlinked-content behavior. Implementation must cover both mutation-time and
restore-time checks; a passing insertion test alone is insufficient.
