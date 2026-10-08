# Correction impact preview

Implemented 2026-10-08. Read-only preparation for explicit replacement publication.

The correction editor can load or refresh the saved draft's impact: active directly referenced review cards, directly linked code exercises, current source passages and source/version checks. Unsaved edits and changed revisions are labeled. Failed refresh keeps the previous preview visible with an error. Excerpts are limited to 6,000 characters and explicitly marked when truncated; missing sources remain unknown.

An opaque preview token binds the draft, current original and question state, source evidence/passages and exact affected IDs. It is not publication authorization. No grades, learning evidence, schedules, eligibility or curriculum are changed, and no model calls are made.

## Verification

- 19 backend tests: impact, validation and draft API; ownership, read-only behavior, count filters, stable/change-sensitive tokens, truncation and missing sources.
- 9 frontend tests: impact and editor; explicit loading, dirty/revision warnings and retained preview on refresh failure.
- 2 real sandbox Chromium journeys at 390 and 1280 pixels: keyboard preview loading plus existing save/recovery/navigation regression.
- Both screenshots inspected: readable, no horizontal overflow. Browser seed has no source passage; passage rendering is covered by component tests.
- Ruff, strict mypy (216 source files), frontend lint, TypeScript and production build pass. Existing bundle-size warning remains.
- Bounded code/pedagogy review: no blockers or major findings.

## Remaining

Publication remains disabled. Next implement the atomic, repeat-safe publish command and explicit UI confirmation under the replacement plan. Counts currently cover direct references, not transitive replacement-chain consumers. Source status and excerpts are evidence for review, not proof of semantic correctness. Saved-draft checks repeat some preview status; consolidation is optional future polish. Human comprehension and physical audio are not established by these tests.
