# Saved lesson and hint answers

QA01 continuation: completed tutor explanations, hints and shared text/voice generation now use the same local answer store as workspaces. Persist final TurnDone text after trace/events/checkpoint transactions, not the untrimmed token prefix. Save request, actual selected skill/area, course display label, model/prompt metadata, source citations/flags and hashes of supplied source text without copying corpus passages.

A consumer-aborted generator and a partial model response do not create a completed answer. Database save failure preserves the reply and exposes an unsaved warning. Lesson/hint source panels and voice panel expose saved/unsaved status. Voice stores one text response through the shared producer, not another record per audio chunk; saving does not mean the audio was heard.

No migration, extra model call or evidence write. Request-level replay/save retry, stable workspace scope and original question/action separation, representation/assessment links, search/suggestions remain pending. Course labels alone are not stable course identities. Source hashes identify supplied text versions; missing corpus after restore remains unavailable, not verified.

Verification: 430 backend tests and 202 frontend tests pass; lint/types and production build pass. Completion/partial/save failure and generator cancellation tested; source snapshots and exact final text asserted. Independent code/pedagogy review found a major canonical-text mismatch in streamed UI; fixed with completed/partial regressions and voice synchronization, re-review clear. Old test fixtures lacking required final text corrected. Isolated reader and hint/source journeys checked before publication. No live-model quality claim; existing build warnings remain.
