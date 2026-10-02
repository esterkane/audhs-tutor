# Reviewed preferred correction and undo

A learner opening a proposed correction can compare the original, explicitly confirm review of
both answers, and prefer the correction. The choice is a preference, not verified correctness or
mastery. Original and correction remain immutable and readable. Every answer can display its
current preferred correction and undo it; source/context/feedback checks still apply independently.

The separate owner-scoped tutor_answer_replacement table stores original, nullable preferred ID,
revision and timestamp. GET is read-only. PUT accepts only an owned direct proposed-correction child,
rejecting self/unrelated/hidden/incorrect/outdated/already-replaced targets. Revision-checked writes
and harmless same-state retry handle stale/concurrent edits; null reverses the choice without
changing feedback. Existing reports still apply after undo. A later report on the preferred reply
can exclude that reply too; it does not silently restore the original.

Shared eligibility excludes replaced originals from suggestions, workspace lexical/exact reuse,
lesson memory, vector loading and index population. Ordinary history and explicit follow-up remain
available. Corrections are not automatically promoted past existing evidence/context restrictions.
UI GET/PUT have 15-second deadlines, abort/disposal guards and late-response protection; uncertain
writes permit same-choice retry and explicit latest-state review. No model call or learning event.

Migration 9c2187eaf014 was prepared outside the watched migration directory and upgraded a disposable
consistent working-database snapshot, with foreign keys checked, before the complete revision was
published. The working backend then auto-migrated to that revision; its foreign-key check is clean.
The table participates in learner export/wipe and populated full/encrypted backups via
existing table discovery. No acquired material, secrets or runtime database enter sanitized source.

## Verification

Tests cover owner/target eligibility, unchanged text, history vs suggestions, same-state retry,
stale revision, concurrent one-winner choices, undo and export/wipe. Browser desktop/narrow journeys
exercise compare/review/choose/undo with keyboard. Code review found stalled PUT risk; added bounded
GET/PUT and an abort-resistant late-response regression. Code re-review and pedagogy review have
no remaining blockers/majors. Backend595/frontend279, lint/types/build and two desktop/narrow
browser journeys passed. Sanitized backend45 (including populated backup/migration/export/wipe
and reuse consumers) and UI3 passed. The schema-inventory assertion was updated for the new table.
Existing build chunk warning remains. Prior CI passed in both repositories (36946801854/36946812124).

The preference is reversible current state; this slice does not claim an immutable audit of every
past preference edit or live-model correction quality. Personal voice and broader queues remain open.
