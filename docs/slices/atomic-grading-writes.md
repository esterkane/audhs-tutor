# Atomic grading learning writes (R3 / F04)

Learners must not get a partial attempt, evidence contribution or review schedule after an interrupted grade.
The shared Grader owns one short transaction after inference finishes; kernel helpers optionally flush.
Attempt, attempted/graded/evidenced/reviewed events, competency evidence/state, review item/log/card and
hint checkpoint reset succeed together. Model accounting and recoverable answer history stay separate.
No schema/API/UI change; optional confidence, accessible controls and mode/energy behavior are unchanged.

## Reproduction and implementation
A fresh-connection regression injected failure after the attempted event and observed an already-committed
attempt/event. The grader now uses commit=False kernel/event calls and one final commit, rolling back
on exceptions and cancellation. Existing helper callers retain commit=True defaults.

## Verification
Fresh-connection failure tests cover nine boundaries with new and already-reviewed items. Additional
semantic-grading tests prove both exceptions and cancellation preserve one model-call record while
learning rows roll back. Full backend629 passed; final expanded boundary tests18 passed; lint/types passed. Required code and pedagogy reviews found no blockers or majors. Existing library warnings remain unchanged.

## Limits
This resolves partial learning writes, not the entire R3 gate. Durable request completion still follows
the learning commit and recoverable answer-history save; interruption in that gap remains unresolved
and never automatically regrades. Review-rating idempotency and content-version conflicts remain open.
No schema migration; no live data edits or paid provider calls are needed for this slice.
