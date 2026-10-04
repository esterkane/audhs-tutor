# C6 saved-thought action feedback

## Problem and implementation

“Promote to next session” displayed the thought on Home immediately, while “Drop”/“Done” removed it from visible lists without feedback or recovery. Failed mutations were silent. Baseline browser reproduction confirmed that a failed promotion gave no alert.

Rename the action “Show on Home” and Home's list “Thoughts to revisit.” Removal has an explicit inline confirmation, initially focused on Keep thought, with an honest no-undo warning. Keep returns focus to the original action. Pending writes are synchronously guarded; status/error messages identify the affected thought. Mutation waits have a 15-second deadline and no automatic retry, and invalidate lists on settlement to recheck actual server state. Failures disclose uncertainty rather than claim rollback. Focus returns to result feedback when the initiating control disappears or becomes disabled, without taking it from another focused control.

Same backend statuses, endpoints and learning semantics; no new library or schema. Both former Drop and Done used the same backend removal operation; the clearer removal action retains that functionality. Initial browser tests exposed focus loss during disabling; corrected before publication.

## Evidence

18 relevant Home/capture/draft component tests passed. Browser coverage combines the seven existing capture recovery journeys with four action journeys: failed promotion retains visible thought/error; keyboard Keep and explicit removal at390/1280; confirmed Home destination; focus after removal; stalled action unlocks without duplicate or automatic submissions. Desktop and narrow confirmation screenshots inspected. Lint, types and production build passed; inherited bundle/worker warnings remain. Read-only code/state and pedagogy reviews found no major regressions; safer initial Keep focus adopted.

## Remaining limitations and next boundary

There is still no backend undo or server-side idempotency. Confirmation reduces accidental removal; it does not replace the authoritative longer-term reversible workflow. Exact source/notebook return and mutation atomicity remain in capture-recovery-contract.md. Physical/assistive-technology and owner comprehension checks are not claimed. Next reconcile remaining C6 Home Resume/Review/Recent composition against actual data before starting C7 recent-context/global-search work; do not substitute further parking polish for the broader workspace design.
