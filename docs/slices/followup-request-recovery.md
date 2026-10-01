# Saved-answer follow-up request recovery

Status: implemented and verified.

A learner can retry a lost follow-up response without generating another reply or changing its parent.
Input is the owned parent answer, session, exact question and optional UUID transport identity.
The existing durable ledger fingerprints the route and parent along with the typed body; replay
returns the original response before rebuilding historical context. No replay events or mastery.
The UI retains the frozen parent/question in this tab and offers explicit retry/new-work controls,
with the same storage-denial limits, accessible buttons and no mode/energy adaptation.

Acceptance: owner/parent isolation, concurrent duplicate and lost-response replay, unchanged
model/event counts and parent lineage; pending request across reload; stale callbacks and typed
edits; shared workspace recovery regressions; isolated keyboard/narrow journey; lint/build/review.
A changed feedback report must not silently turn a transport retry into new inference. A new
request explicitly uses the current parent report. Lesson streams/voice remain separate.

## Verification and limits

Full backend570 and frontend243 tests passed. Lint/format/mypy/TypeScript/ESLint and
production build passed. Seven isolated Chromium journeys passed: two desktop/narrow
follow-up reload/keyboard retries plus the five workspace/storage-denial regressions.
Browser transport uses fake responses; backend tests assert actual unchanged model/event
counts, immutable parent lineage, owner isolation, differing-parent/payload conflicts,
concurrent duplicate status and replay after feedback changes/session ending. No paid call.

The shared retry hook now validates workspace and follow-up payloads separately. Follow-up
requests preserve original parent/session/question across reload; edits made before retry
remain as the next draft. Recovery never automatically resubmits on mount. Same browser-tab
storage limits and explicit in-memory opt-in apply. Closing the tab or wiping browser data
can lose the client's retry identity; the API ledger remains learner-owned durable state.

Required code/pedagogy reviews found no blockers or majors. Minor wording was tailored to
“original parent answer and question.” A changed parent report is included only in a new
request, not used to regenerate a completed retry. Deleting the original parent blocks replay.
Existing signed-save receipt expiry/restart limits remain; this does not claim exactly-once
provider execution or lesson/voice stream recovery. No migration or new dependency.
