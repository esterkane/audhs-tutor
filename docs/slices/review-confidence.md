# Slice: review-confidence (P1, 2026-09-20)

**Story.** Before revealing a review card the learner rates their recall confidence; that rating is stored with the FSRS review and cleared for the next card (review finding 2: it was collected but never sent, and leaked to the next card).
**In/out.** `Review.tsx` sends `confidence_pre` in `POST /api/review/{item_id}` (the API already accepted it; `memory.review` stores it on the `reviewed` event) and resets it after each rating; a failed rating shows an alert and keeps the card. The review screen knows whether it runs inside a planned review block (`SessionOut.state`): then "Continue the plan" advances on the server and "Stop here" ends the block with `save_and_stop`; outside a review block it says so ("off-plan review") and does not touch the plan.
**Events.** `reviewed.result.confidence_pre` (1–5) now populated from the UI; no schema change.
**Mode/energy.** The minimum-viable cap and the explicit "show all" undo are unchanged.
**Accessibility.** "Show answer" stays disabled until a confidence is chosen for *this* card; ratings are buttons with literal labels.
**Verified by.** `Review.test.tsx` (two cards: confidence 4 then 2 posted, reset in between, block advance) and `test_session_transitions.py::test_review_confidence_is_recorded_per_card` (event payload).
**Review fixes (2026-09-20).** `stopHere()` returns early while a transition is pending and catches errors (the block is closed as `save_and_stop`, not later as `session_end`); the off-plan note distinguishes the *current* from the *last* block; the review block's soft timer is not shown on this screen (open: planned minutes of a review block are not surfaced — the cap already bounds it).
