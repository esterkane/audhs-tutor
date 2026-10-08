# Internal correction publication transaction

Implemented 2026-10-08; HTTP publication and confirmation UI remain disabled.

The internal service serializes on the learner write lock, replays an identical command before freshness checks, and rejects stale draft/preview/content/source/state. It accepts active or deliberately suspended originals, validates the extended ancestry, creates a learner-owned assessment and fresh rubric, supersedes the old question, and records the published draft and immutable result receipt in one caller-owned transaction. No historical IDs, grades, review rows, memory schedules or competency evidence are rewritten.

Published drafts resolve exactly their attached report through the published status and immutable feedback association. Inbox exclusion occurs after ranking; earlier reports do not reappear. The original report is retained. Withdrawn or changed attached reports block publication. Code/listening and incomplete source evidence remain gated; source review is not a correctness guarantee.

Migration c146f830ad92 expands the draft status constraint. Downgrade refuses published drafts. Published editor content is read-only and correctly labeled. No real question has been published; no live database migration applied for this slice.

## Evidence

37 backend tests pass across publication, impact, API, inbox, migration and visibility. Includes concurrent same/different request IDs, stale impact, original preservation and other learner isolation, suspended originals, chained replacements, report retention/resolution and rollback after each of four explicit write flushes including a new rubric. Migration preserves existing drafts/receipts and validates foreign keys.

Ruff and strict mypy (217 files) pass. Editor tests:8 pass after published-status regression; earlier editor/impact combined9 pass before that added test. Frontend lint, types/build pass with existing bundle-size warning. Two sandbox Chromium keyboard/save/reload journeys pass at390/1280; narrow screenshot inspected. These browser tests cover existing editing, not publication. Independent code/pedagogy review clear after report-resolution fix.

## Next acceptance

Expose explicit publication only with saved preview confirmation, same-command lost-response lookup/retry, pending-edit protection and integrated report-to-replacement sandbox journeys. Add missing/incomplete-source and unsupported-kind endpoint cases. Reversal remains a separate explicit policy; never restore superseded content through the suspension endpoint. Human comprehension and full release acceptance remain open.
