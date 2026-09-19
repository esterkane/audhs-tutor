# Slice: fsrs-memory (Stage 1)

**Story.** Anything the learner has answered comes back for review when FSRS says it is about to be forgotten, and never more than the minimum-viable amount for today's mode and energy.
**In/out.** `kernel/memory.py` (py-fsrs `Scheduler(desired_retention=0.9)`; `ensure_item`, `due_items(now, cap)`, `review(rating 1–4, now)`, `mean_retrievability`, `review_cap(mode, energy)`: low-capacity 5, steady 10, novelty 15, energy ≤ 2 → 5). `GET /api/review/due?session_id[&as_of]` returns capped items with question + `reveal` (answer/explanation/rubric) and honest totals; `POST /api/review/{item_id}` rates and returns the new due date and predicted retrievability. `as_of` is the dev/benchmark time-travel hook.
**Kernel rule.** Only `memory.py` writes `memory_state`; the recall dimension of competency blends mean retrievability (ADR-0004).
**Events.** `reviewed{rating, latency_ms, predicted_retrievability, days_since_learned, stability_before/after}`.
**Verified by.** `tests/test_kernel.py::test_fsrs_memory_review_and_time_travel`, `::test_review_cap_and_rating_rules`, `tests/test_api.py` (due after 2+ days, rating).
