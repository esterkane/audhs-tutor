# Private experiment access

A foreign private unit must not influence experiment balancing, counts, metrics or API labels.
Resolve experiment ownership before assignment, refuse known foreign skills/sessions and foreign
session context, and use one scoped assignment query for balancing, analysis and API lists/counts.
Missing historical unit IDs retain existing behavior. No new events, models, scoring formula,
mode/energy or UI behavior. Authorized assignments retain the existing event contract.

Rows must match learner, experiment unit type and an arm of that experiment. Known foreign units
are excluded before outcome aggregation. Hidden legacy collisions return a conflict without
fabricating an idempotent success. Existing shared/owned units retain balanced deterministic
assignment. Defensive fixture corruption verifies read-side exclusion independently of producers.

Verification:1594 backend tests,17 focused regressions,lint/types and bounded code/pedagogy
review pass. Logs: `/tmp/private-experiments-full.log`, `/tmp/private-experiments-focused4.log`,
`/tmp/private-experiments-lint.log`. Tests confirm unchanged valid balancing and no counts,
outcomes or writes for known foreign units. No blockers or majors remain in the bounded review.
No visual/keyboard behavior changes. This does not establish storage-level experiment constraints
or complete private-content isolation. Retrieval/permissions and activation lineage remain open;
private lesson producers remain disabled.

## Next direct-read audit findings

`kernel/curriculum.py` still has unscoped course counts and skill/slug maps/upserts;
`kernel/seed.py`, `practice.py`, `listening.py` and `vocab_import.py` also resolve shared
content by global slug. Before private producers open, shared-content writers must refuse
collisions with private nodes rather than modifying or adopting them. Scope course counts
and prerequisite maps to their intended learner/shared context. This inventory is evidence
for the next bounded change, not proof that all remaining reads are covered.
