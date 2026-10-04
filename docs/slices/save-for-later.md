# C6 Save for later and audio audit

## Problem and implementation

“Park” did not explain the capture action or where to find saved ideas. Rename the shell trigger to “Save for later,” the dialog to “Save a thought for later,” and its list disclosure to “Saved thoughts.” Success feedback names that retrieval path. Preserve existing session/skill payload association, list promotion and discard functionality.

Inspection also found unhandled save rejection and repeated submission. Guard one in-flight save synchronously, retain the draft on failure, and disclose uncertain server outcome. A 15-second response deadline aborts the local wait and unlocks editing; Promise.race plus request identity prevents late responses from clearing newer text. Closing during submission is labeled Close and explicitly does not cancel the server save. Saved-thought list loading/error states are distinct from empty results.

No backend/schema, learning-kernel, provider or dependency change. api.park adds only an optional browser AbortSignal. Existing styles are retained.

## Verification

Baseline: five audio/capture browser journeys passed before edits. Final coverage: seven browser journeys, nine capture/audio component tests, lint, types and production build. Browser scenarios cover 320/390/1280 widths with 200% text size, keyboard open/save/Escape/focus return, retained draft, one pending request, failure and list-error feedback, timeout/late response. Inspected desktop failure and narrow saved-state screenshots. Audio scenarios verify settings retention, keyboard Stop while details are collapsed, preparation/paused/completed states. They do not establish Bluetooth audibility.

Code/state review found the initially unbounded wait; resolved with deadline and recovery. Pedagogy review found misleading Cancel during saving; resolved with Close and explicit outcome copy. Both final reviews cleared the slice.

## Remaining architecture and acceptance

The parking API has no server idempotency guarantee. A lost response followed by retry can duplicate a thought: disclose uncertainty and check saved items; future reliability work should define durable intent identity before claiming exactly-once effects. Draft is in memory, not refresh-proof. Existing context associates session/skill, not a durable route/notebook checkpoint; this is insufficient for the authoritative recent-context return design. Define that contract in C7 before expanding stored fields. Promotion/drop feedback and reversibility need a subsequent focused audit. Home composition and human comprehension remain open; C6 is not declared complete. Physical voice/headphone and assistive-technology acceptance remain separate.
