# Private curriculum ownership foundation

Adds nullable SkillNode.owner_learner_id, preserving existing shared nodes. Explicit
content_access predicates and require helpers resolve shared-or-owned skills,
learning objects and representations; missing learner scope is shared-only and
foreign/missing IDs have identical errors. No private producer or activation is enabled.

Private inherited content now participates in learner export and dependency-ordered
wipe, including representations without model-call attribution. Shared prerequisites
and another owner's content remain. Downgrade refuses while private nodes exist.

This is not app-wide isolation: immutable ownership/edge/assessment constraints and
migration of every consumer/cache/index remain required before private activation.
The existing promotion publication guard stays in place. Helpers use standard session
autoflush/populate_existing; callers must manage pending edits and transactions.
No model, UI, learning evidence, scheduling or grading behavior changes.

## Verification
Three focused tests cover A/B/shared access through all three read helpers (including
already loaded ORM rows), private export/wipe with enforced foreign keys, and populated
upgrade/refused downgrade/re-upgrade. Disposable migration against a consistent live
DB copy passes. Full backend suite: 1,578 passed; an additional revision-pinned downgrade regression passes with the five-test lesson-storage suite. Lint/types pass. Migration applied after disposable verification.
Bounded code/architecture review: no blockers or majors; scope limits retained.
UI/browser checks are unchanged and not rerun for this unused storage/read foundation.
