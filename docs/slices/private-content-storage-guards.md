# Private content storage guards

Private curriculum ownership must survive direct SQL updates and recovery, not only service calls.
SQLite guards reject skill/assessment ownership changes, cross-owner object/representation moves, invalid
private edges, and assessments whose owner differs from a private parent skill. Shared and
same-owner relationships retain existing behavior. No new learning event, scoring, model call,
mode/energy or UI behavior; accessibility is unchanged.

## Design

Revision52443d30fac9 validates existing edges/assessments before installing any guard. Invalid
legacy relationships cause refusal without rewriting content. ORM create_all installs identical
DDL. Null-aware comparisons include accidental publication by assigning a null owner.
Downgrade refuses while private skills or assessments exist, before dropping any guards.
Objects and representations may move within the same ownership scope; cross-scope moves fail.
Shared-to-private edges and private assessments on shared skills remain allowed by contract.

Backup validation accepts older revisions for migration, requires the new guards from their
introduction revision onward, and compares their SQL definitions, not only their names. After
upgrade it validates existing relationships plus foreign keys. Restore remains staged/atomic.
Defensive-read tests explicitly bypass guards only in disposable fixtures to retain invalid-data
coverage. The original ownership-column regression is pinned to that migration's revision.

## Verification

Expanded focused suite:66 passed; earlier access/migration group:23 passed. Final lint/types
and copied-live-database migration check pass. Final full suite:1591 passed (three dependency warnings); the subsequently added
assessment-only downgrade regression passes in the six-test guard suite. Final test-file lint/format
checks pass. Migration applied to the live database only after disposable-copy and review gates. Bounded review major fixed:
assessment ownership is immutable even after reparenting to a shared skill, closing direct and
two-step declassification. Regression tests cover both. Initial backup-only run passed29 assertions
but aborted in native-library shutdown; expanded rerun completed cleanly. The first full run was
explicitly interrupted for the review fix and is not counted as passing. An intermediate full run
found one downgrade-revision regression (1589 passed); fixed with a populated preflight and
18 passing migration/storage checks. Older revision-provenance tests are pinned to the relevant
revision so they still exercise their original safeguard rather than a later guard.

## Remaining

These guards enforce storage relationships, not caller authorization: a caller still needs the
scoped services for inserting learner-owned records. Experiment assignment/aggregate access,
remaining retrieval/permissions and immutable activation lineage are not closed by this slice.
Private producers stay disabled. No lesson is activated or assessment qualified.


Logs: `/tmp/content-guards-full4.log`, `/tmp/content-guards-lint4.log`,
`/tmp/content-guards-migrate2.log`, `/tmp/content-guards-final-focused.log`,
`/tmp/content-guards-live-migration.log`. No frontend behavior changed; browser/keyboard
checks are not a claim made by this backend-only slice.
