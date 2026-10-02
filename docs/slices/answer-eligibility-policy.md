# Shared saved-answer eligibility

Replacement selection must exclude superseded originals from every automatic reuse path, while
preserving readable history. Current exclusions were duplicated in five places. This prerequisite
centralizes owner-scoped hidden/incorrect/outdated exclusions in db/answer_eligibility.py and uses
it for suggestion lists, workspace lexical/exact reuse, lesson memory, semantic vector loading
and vector index population. Query limits, source checks, scopes and ordinary history are unchanged.

Existing tests for feedback, workspace/lesson memory, vectors and index population exercise all
five consumers (24 focused tests passed). Required code review found no blockers/majors. No UI,
model prompt, migration, new dependency, learning evidence or live-data mutation. Final full-suite
and lint/types passed: backend592. Sanitized focused24 passed as well.

Next: add a separate revision-checked learner replacement choice (original -> reviewed direct
correction, or null to undo). Do not overload hidden/feedback fields or rewrite answer metadata.
Keep same-state retries harmless and reject stale revisions/foreign/self/unrelated targets. The
single policy can then exclude replaced originals consistently. Choosing a preferred answer is
not correctness verification, mastery or automatic promotion into incompatible request contexts.
