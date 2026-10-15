# Stale plan recovery — proposed learner interaction

Status: owner approved “Review an updated plan” on 2026-10-15. Implemented in a bounded slice; see [verification and remaining gates](../slices/stale-plan-recovery.md).

## Reproduced risk

Plan proposals and undo retain whole-plan snapshots. Advancing from activity 0 to activity 1 before accepting/undoing can replace activity 1's planned duration while it is running. Atomic persistence does not prevent that semantic change. Regression: tests/test_plan_snapshot_conflict.py; the test requires completed/current blocks to remain unchanged.

## Recommended interaction

1. Bind each new proposal to the exact plan revision and activity boundary it was generated from. Bind undo to the accepted revision and boundary.
2. If those no longer match, leave the current plan, checkpoint, decisions and learning evidence unchanged. Explain that the session has moved on; do not call this a network failure or encourage repeating the same action.
3. Offer **Review an updated plan**. This explicit action asks the existing deterministic planner for a new proposal using current energy and the actual server activity boundary. Keep completed/current blocks, start time and timer extension unchanged.
4. Show the newly proposed remaining activities and time before acceptance. Updating the preview does not apply the proposal. Keep the old proposal in history as superseded, not declined or accepted. Do not reuse the old deduplication pattern to block regeneration.
5. For stale Undo, offer a reviewed proposal for the remaining activities using the earlier settings; never restore past/current activity snapshots silently. Label this as a new adjustment, not as exact reversal of historical work.
6. Completed sessions remain read-only. Missing legacy revision metadata is unverified, not current; route it to explicit preview recovery.

## Alternative

Keep the current plan and provide only a stale warning plus manual replanning in session options. This has less implementation surface but leaves more recovery work to the learner. It still needs proposal supersession/deduplication handling and must not falsely promise universal Undo.

## Implementation boundary and gates

Schema/representation: version-bound plan proposal and undo metadata; explicit supersession reason with no fabricated learner decision. Decide whether existing adaptation JSON plus additive response fields are sufficient before choosing a migration.

Kernel/API: compare under the existing writer transaction; refresh uses current server state and owned proposal; no model calls; exact same preview acceptance must remain conditional on its revision. Preserve negative choices and future suggestion preferences independently of proposal identity.

Frontend: distinguish stale conflict from retryable transport failure, show an updated preview and separate accept action, preserve context and focus, keyboard/narrow-screen tests. Update history wording to distinguish a historical applied change from a currently reversible one.

Tests: acceptance/undo after advancement, after later plan changes and after Finish; changed energy; duplicate refresh/accept; concurrent progression; missing legacy metadata; failed saves and reload. Assert no completed/current activity mutation, no fabricated decisions, no mastery/FSRS changes and no model calls. Add real HTTP/storage browser coverage, not only mocked adaptation choices.

This is broader than a transaction fix. Do not silently implement a merge policy or mark the full adaptation lifecycle complete from the existing tests.
