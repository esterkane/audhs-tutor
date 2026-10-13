# Shared writers and private curriculum

Shared curriculum publication, seed loading, vocabulary and listening creation must never adopt
private skill identifiers. Preflight every requested shared slug before writing any skill; return
a generic conflict for private collisions, including the current learner's private node. No private
content is exposed in the error. Existing shared upserts and missing-node creation remain intact.

Curriculum material status counts only shared/current-learner nodes. Shared draft validation and
prerequisite resolution use shared nodes only; private nodes cannot influence shared cycles or be
adopted as prerequisites. Vocabulary preview remains read-only and ignores private deck collisions.
No new learning event, scoring, model call, mode/energy or UI behavior; accessibility unchanged.

## Verification

38 focused tests pass, including both own/foreign private collisions, course visibility, private
prerequisite rejection, seed/publication preflight with a would-be-created earlier skill, and an
explicit commit after refusal proving no partial skill writes. Full suite:1597 passed (three dependency warnings); lint/types and bounded code/pedagogy
review pass with no blockers or majors. Logs: `/tmp/shared-writers-full.log`,
`/tmp/shared-writers-focused.log`, `/tmp/shared-writers-lint.log`.

## Remaining

This is scoped shared-writer protection, not private publication. Private answer-derived lessons
remain guarded. Retrieval/hosted-source permissions, activation lineage/transactions and explicit
activation UI still require their own acceptance gates. No lesson or review evidence was created.
