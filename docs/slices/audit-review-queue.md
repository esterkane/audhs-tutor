# Audit R1a — stable review queue (F02)

User story: changing the review cap or returning to review must not skip an unreviewed card or silently expand the selected workload. Input: session-scoped due cards and explicit Show all. Output: stable card identity and accurate subset completion. Existing rating events and FSRS writes are unchanged; no new event, schema or API payload. Optional confidence, hints, stop and low-capacity cap remain intact. Existing accessible buttons are retained.

## Evidence and implementation

Before fix, a fresh component regression reproduced [A,B] → rate A → Show all returns [B] → false Review done. The test failed on missing B. Queue now stores admitted/reviewed/current/revealed IDs and all flag in a validated v1 tab-local sessionStorage checkpoint; backend ratings remain authoritative. Storage failure falls back to this visit's state, not durable cross-tab recovery. Full draft policy is R4.

Successful ratings checkpoint identity even after unmount. Shared mutation state disables repeated in-flight ratings across remount; Review explicitly opts into due-cache reconciliation. Other useRate consumers retain existing behavior after full-suite discovery of the PracticePanel index assumption. This is not backend idempotency: lost-response/reload duplicate-write protection remains F04/R3.

Completion distinguishes selected-set completion from no currently due cards and offers explicit expansion. Error/retry retains stored ratings. No mastery, planner, confidence, source or model-routing changes.

## Acceptance evidence

Four Review tests cover original reveal/confidence/plan flow, A/B cap-change and revealed remount, partial cap remount with newly due C excluded until Show all, and deferred rating across pending remount/unmount with shared QueryClient. Full frontend and backend suites and project lint recorded in HANDOFF. No browser journey or owner-comprehension pass claimed.

## Reviews

Code and pedagogy reviews found: cap silently expanding; async success lost after unmount; duplicate pending mutation after remount; misleading empty completion after cache removal. All addressed with tests. Final read-only reviews clear blockers/majors for this slice. Inherited changes remain untouched.

## Remaining

R0 full 48-finding evidence ledger is not complete; current source checks and F02 reproduction only. R1 F01 explicit lesson navigation/server checkpoint and F13 focus-screen active topic remain next. R1 is not complete. R3 server idempotency and R4 durable recovery remain separate. No commits/pushes, dependencies, migrations or live learner-data changes.
