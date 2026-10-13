# Private lesson-promotion storage

Persist immutable owned draft/answer binding and retry identity in lesson_promotion.
Store raw lineage separately in lesson_promotion_snapshot: retained in full private
backups, omitted from learner backups; derived draft content remains private.
Composite ownership FKs prevent cross-learner draft/answer/snapshot relationships.
The existing shared curriculum publisher rejects any linked promotion before writes.
No production creation API or command exists yet; no lesson is activated by this slice.
No new events or UX; the next step is transactional idempotent draft creation and
private publication ownership, not bypassing the guard. Snapshot absence after a
learner restore must mean unavailable grounding, never inferred permission.

Migration 30221b1ed8a7 adds only the two tables and owned-parent indexes. Removed
unrelated FTS/assessment alterations emitted by autogeneration. Disposable-copy
upgrade and focused backup/wipe/immutability/downgrade checks pass; 1566 backend tests and lint/types pass (three existing warnings).

Review fixed a major: populated downgrade now refuses before any DDL. The regression
asserts unchanged rows, migration revision and guards, then verifies empty downgrade
and re-upgrade after explicit wipe. Real foreign-owner draft/answer references fail;
valid same-owner references succeed. The older visual-generation downgrade test now
starts at its own revision to continue testing its specific guard. No other review
blockers remain. Private publisher guard is unconditional for linked promotion records,
including after draft edits; caller-provided metadata cannot remove that link.
