# Private activation storage

An eventual explicit activation needs a durable receipt linking its exact edited draft and
origin to every private curriculum row it creates. This slice adds storage only; no producer,
API or UI enables activation. No learning events, competency, review or scheduling writes.
Mode/energy and accessibility behavior are unchanged; no new interaction is exposed.

## Implementation

- Immutable learner-owned header with unique promotion and learner/request identity; typed
  unique links for skills, objects, assessments and edges, with owned composite header FKs.
- Membership checked on insert and retained during object/assessment/edge reparenting.
  Skill-link deletion requires removing dependent links first; ordinary content edits remain.
- Backup validates guard definitions and restored relationships. Learner export includes
  derived receipts; raw promotion snapshots retain their existing scope policy.
- Wipe deletes dependent links first and preserves other learners. Populated downgrade refuses
  before dropping any guard. Migration 969f9ebbe38a adds only the five tables and their guards;
  unrelated autogenerator proposals to remove FTS or rebuild ownership FKs were discarded.
- Reflective fixtures explicitly respect semantic membership order without disabling guards.

## Verification

Final full backend suite: 1607 passed, three dependency warnings. Focused migration, backup, export/wipe and core checks: 37 passed.
Five activation tests pass, including permitted edits followed by restore, prohibited same-owner
moves, cross-owner inserts, header identity constraints, guard tampering and populated downgrade.
Lint/type checks pass; disposable migration of the live database snapshot passes.
Migration applied after those gates. Five activation regressions also pass in the sanitized
checkout; publication guard passes.
Initial full run: 1603 passed, three legacy revision/guard expectations failed.
Updated latest-schema validation and retained a pinned test of the original ownership guard;
all 11 affected regressions pass. Final full run passes.
Bounded storage review: no remaining blocker/major. No browser verification claimed for this
storage-only slice. Existing runtime remains unchanged until a future command uses these tables.

## Remaining

Atomic idempotent activation command, source/draft revalidation, multi-entity/concurrency/rollback
command tests, receipt API and explicit activation/recovery UI remain unimplemented. Storage does
not qualify tasks, verify facts, confer source permissions or authorize additional activations.
