# Atomic session-plan acceptance and undo

Four baseline failures reproduced: accepting/undoing a plan after Finish rewrote completed history; a version-update failure left the replacement plan committed without its decision. Session-plan acceptance and undo now hold the owned open-session transaction through plan replacement, checkpoint version, decision and audit events. Errors/cancellation roll back together. Declines serialize against acceptance but remain available after Finish. API-supplied session context is owner checked; mismatched and sessionless plan proposals are rejected.

Preference adaptations and trial expiry retain their existing behavior. No schema, inference, grading or scheduling change. Undo's event is now associated with the actual plan session. Completed session plans are no longer shown as in effect, so the existing UI does not offer an invalid Undo; the historical decision remains intact. This changes neither the offered plan nor the requirement for explicit acceptance.

## Evidence

- 72 affected backend tests pass: adaptation, ordinary session transitions, standalone lifecycle and the new acceptance/undo cases.
- Cancellation is tested at the kernel boundary because ASGI middleware converts task cancellation into a missing-response error; no claim that the transport propagates CancelledError unchanged.
- Source code and pedagogy reviews found no blocker/major. Reviewer-requested both-order Finish tests and foreign/missing context tests are included. A final focused test also rejects sessionless malformed plans.
- Final focused23 lifecycle cases cover malformed proposals and completed-plan history as well. Four desktop/narrow keyboard browser cases pass; adaptation choices use HTTP fixtures, while persistence/concurrency is tested against real disposable SQLite above. Narrow adaptation-log screenshot inspected. Full lint/types pass after the final history change.

## Remaining issue

Whole-plan snapshots can become stale after advancement or another accepted plan. Transaction atomicity alone cannot preserve the meaning of undo in those cases. Next: reproduce snapshot conflicts and define a reviewed stale-plan contract; do not silently rebase a proposal or claim all adaptation behavior is safe. Preference-path atomicity, internal tutor checkpoint writes and human usability acceptance remain open.
