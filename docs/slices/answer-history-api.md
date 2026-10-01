# Read-only saved answer history

QA02 foundation: list and open the current learner's completed saved answers without any generation, grading or learning-event write. GET /api/answers uses bounded keyset pagination by immutable answer ID, with optional skill, area and surface filters; GET /api/answers/{id} returns the exact snapshot. Foreign/missing IDs and cursors are indistinguishable. Lists omit full workspace context; details preserve it for the owner.

Request text is labeled as a request, not a guaranteed verbatim learner question: existing action prompts remain distinguishable only after the planned request-context change. Unknown workspace area/skill stays unknown, never assigned from current preferences. Course/step filters, full-text search, browser history UI/suggestions, freshness/correction and replay remain pending. No migration or new dependency; this endpoint is not the full QA02 gate.

Regression: owner/foreign fixtures, paging without repeats, filters/empty states, validation bounds, exact text/context, equivalent denials and zero model calls/events. 434 backend tests and full lint/types pass; generated API types updated. Independent code/pedagogy review found no blockers or majors. No UI change or new browser/model-quality claim. Targeted history/store tests also pass in the sanitized checkout.
