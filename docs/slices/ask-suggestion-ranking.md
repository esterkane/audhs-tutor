# G3b — Local feedback-aware Ask suggestions

Current problem: saved-question suggestions are ordered by recency, so a newer
confusing or stale-source answer can displace an older useful match. G3a already
shows source currency. Add deterministic ranking without automatic answer reuse.

Use a dedicated bounded /ask/suggestions read, preserving history pagination.
Scope by learner and optional area, retain existing negative/hidden/replaced and
assessment exclusions. Match local question words (prefix on final word), give
identical trimmed question text priority, then prefer candidates without known
direct-source or prior-context risks, then helpful/neutral/confusing feedback.
Feedback is a learner report, never a factual score. Reopening remains explicit,
and asking fresh remains available. No model calls, new dependencies or learning
state changes. Rank at most 100 candidates and return at most 10; exact text matches
are considered before recency in that bounded pool. Document that bound.

Affected files: deterministic DB suggestion service, thin Ask route, summary schema,
Ask query and explanation labels, focused source/feedback/ranking tests and existing
keyboard/responsive journeys. No prompt/assessment/FSRS/competency changes.
Accuracy-review aggregation, semantic matching, transitive source lineage and
automatic exact-result reuse remain separate open work. This is not full G3.

## Evidence and boundaries

Focused backend regression: 10 passed (ranking, saved answers, feedback, source
currency). Tests include old exact match beyond 100 newer partial matches, owner
and area scope, unrelated Helpful exclusion, changed feedback, source/context risk,
and no model-call or learning-event writes. Browser: all 12 Ask scenarios passed,
including desktop1280/narrow390 keyboard suggestions, saved feedback disclosure,
follow-ups, stop/recovery, source attachments and reference-copy actions.
Component coverage adds the explicit Helpful-is-not-correctness label. Screenshots
inspected; controls wrap and original session behavior remains unchanged.
Required code/pedagogy review found no blockers or majors.

The candidate pool is limited to 100 (exact text matches before recency); ordering
within that pool is deterministic. No semantic-model matching or fabricated FAQ.
Partial matching reuses the historical FTS request label (text/question). Some
non-Ask learner_question values are not indexed and can be missed unless exactly
matched. This inherited index gap is recorded for a later bounded migration.
A Helpful report is not a correctness judgment; review receipts are not yet ranking
inputs. No model or paid requests were made for this slice. Live synthetic unmatched
query returned HTTP200/empty in 25ms; this is a single smoke observation, not a
latency benchmark or an answer-quality claim. Human/AT acceptance remains open.

Final regression: full backend1,428 passed; full frontend656 passed; all12 Ask
browser scenarios passed. Full ruff/format/mypy, TypeScript/ESLint and production
build passed (existing dependency externalization/chunk-size warnings). Private
SQLite snapshot verified unchanged. Both publication variants remain private.
