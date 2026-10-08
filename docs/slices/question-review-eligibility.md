# R5 — suspended questions in review queues

Story: once a question is suspended, an already queued review must not ask or record a new rating for it. Restoring eligibility preserves the original schedule and requires a fresh displayed view.
This slice connects the state foundation to review selection, direct refresh and final rating checks. No suspension UI/action is exposed yet; assessment selection and recovery integration remain required.
No grading policy, historical evidence, stored FSRS state, mode/energy or sensory preference is changed by suspension. No model calls or new dependencies.

## Concrete issue and implementation

Five baseline tests failed: due selection still returned a suspended question; restore accepted an old view; final rating ignored a same-transaction suspension; reference/learner isolation was unenforced; direct kernel review bypassed status. Completed replay already behaved correctly.

`question_state.py` centralizes the existing assessment_id/nonempty-ref lookup and a learner-scoped correlated eligibility predicate. Vocabulary references are deliberately excluded. `review_content.py` joins state/revision in its single snapshot and includes both in the opaque token; effective activity excludes suspended/superseded/retired questions. Existing endpoint validation and commit-time validation now cover status changes. `memory.py` filters due queues and available-card counts and checks direct rating eligibility under SQLite's write lock.

Historical `mean_retrievability` is deliberately unchanged: removing a question from future practice must not erase its previous evidence or silently recalculate mastery. Summary item/due counts describe currently available cards; the memory signal describes recorded history. Independently inactive cards remain inactive on restore. Completed request replay still returns the original result without new scheduling or evidence.

## Remaining gates

No live mutation or migration, no new UI and no claimed end-user suspension feature. Next connect ordinary/challenge/code/listening selection, generation and assessment direct/recovery paths before exposing suspend/restore. Global R5 replacement/preview and browser keyboard/narrow acceptance remain open. Caller-owned rollback remains required after failed direct kernel writes.

## Verification — 2026-10-08

Baseline: five failed, one passed in the new review integration tests. Full backend run:952 passed and one compatibility failure (unknown item error type). Restored the existing KeyError contract; final46 affected review/content/retry/state tests pass, including that regression and all eight new eligibility tests. Full suite was not repeated after this bounded error-path correction. Ruff and strict mypy206 pass. Bounded code/learning-semantics review found no blockers or majors. No frontend behavior was introduced, so browser/visual checks remain part of the forthcoming UI integration.

Evidence: /tmp/question-review-{before,full,final,ruff,mypy}.log. Separate tests verify vocabulary/ref precedence, learner isolation, completed replay, same-transaction suspension, restoration with fresh token, disabled-card preservation and unchanged historical retrievability.
