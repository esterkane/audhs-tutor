# Saved answer retrieval before tutoring

For explicit workspace tutor requests, search owner-scoped local answer history before generation and provide at most two short relevant excerpts.
Require a selected target and matching supplied workspace; exclude hidden/incorrect/outdated replies and prior memory-derived replies to avoid recursive reinforcement.
Previous answers are untrusted historical context, never corpus evidence, execution results or mastery. Preserve the current question, teaching intent and model route.
No automatic direct replay yet. Expose reused answer IDs and dates; retrieval failure must not prevent tutoring. No sound/motion or mode change.
Acceptance: owner/target/workspace isolation, feedback exclusions, bounded escaped excerpts, no recursive memory, query failure recovery, visible provenance, and model-contract review.

Verification: 442 backend tests, full frontend suite passed (222 tests before final reopen regression), 26 focused tutor/history tests after review fix, lint/types/build, desktop/narrow notebook journeys. Independent code/pedagogy review fixed hidden provenance on reopening; re-review clear. Local-model quality and latency evaluation pending. No model calls avoided yet. Literal search uses at most 200 question characters and 20 recent candidates; semantic recall is not implemented.
