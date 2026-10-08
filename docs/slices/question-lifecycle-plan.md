# R5 question lifecycle: current-code reconciliation

Status: design preparation, not implemented. Scope: F05/U08; no live content changes.

## Confirmed problem

`Assessment` has no eligibility state or revision. Curriculum publication compares question content and appends distinct assessments; it does not replace the old question. Question feedback records a snapshot/preference event, correctly without changing mastery, but cannot explicitly suspend a question. Consequently publishing a corrected question does not guarantee the original stops appearing.

This cannot safely be fixed by hiding a UI card or setting one ReviewItem.active flag. Selection is distributed and already queued items have their own paths.

## Required integration map

- `db/models.py`: Assessment identity/content; learner-scoped ReviewItem and historical AssessmentAttempt/ReviewLog.
- `orchestrator/grader.py`: ordinary selection and direct grading; `orchestrator/challenge.py`: challenge selection.
- `kernel/exercises.py`: generated exercise/check lookup and creation; suspension must not silently recreate an equivalent question.
- `kernel/listening.py`: listening selection and direct lookup; historical attempt counting must remain intact.
- `api/sessions.py`: stopping after explanation can create a first assessment review card.
- `kernel/memory.py`: find/create cards, due eligibility and summary denominators; do not overwrite independently inactive cards on restoration.
- `kernel/review_content.py`, `api/review.py`: queued-item refresh and version-bound rating.
- `api/assess.py`, `api/exercises.py`, `orchestrator/assessment_content.py`: direct-ID access, content snapshots, new-submission validation and commit-time lock validation.
- `orchestrator/assessment_requests.py`: completed replay must survive suspension; prepared continuation must not bypass current eligibility. Uncertain inference outcomes must remain uncertain.
- `kernel/curriculum.py`: additive publication needs an explicit replacement mapping and preview; deduplication must not silently reactivate suspended material.
- `kernel/question_feedback.py`: reporting remains separate from explicit eligibility actions.

## Proposed contract, pending bounded implementation review

Use learner-scoped eligibility/revision records rather than a global flag: Assessment is shared, while the explicit action is a learner choice. Absence means active for migration compatibility. States: active, suspended, superseded, retired. Keep immutable assessment IDs and old attempts. Store actor, reason, transition time and replacement ID separately from assessment content identity. Do not encode eligibility in item_json.

First vertical slice: explicit suspend/restore, optimistic expected revision, repeat-safe request identity, one reusable eligibility predicate used by every selector above. Restore only suspended items; superseded/retired require their own explicit policy, never a generic toggle. Do not mutate existing card activity flags to implement suspension: filter by underlying assessment eligibility so restoration cannot revive independently disabled cards. Apply the same eligibility check at direct reads and immediately before committing new learning evidence under the same transaction. Preserve old completed outcomes as historical replay, not new grading.

UI: separate “Report a problem” from “Stop asking this question”. Explain that historical answers remain and progress is not recalculated. Show affected queued review count and explicit restore. If a displayed item becomes unavailable, retain the learner's answer and offer another question; never silently grade a different item.

Second slice: correction inbox and replacement preview showing old/new question, source provenance, affected pending reviews and preserved history. Publication atomically creates the replacement and supersedes the selected original with expected revisions and request identity. Do not transfer old mastery or FSRS state to the replacement without a separately reviewed learning policy.

## Acceptance before shipping

1. All ordinary/challenge/code/listening/session-stop selectors exclude suspended items; generation cannot resurrect them.
2. Already queued review refresh/rating and direct assessment IDs cannot bypass suspension.
3. Completed replay remains readable; prepared continuation and in-flight commit respect eligibility changes without duplicate inference/evidence.
4. Suspend/restore preserve attempts, logs, scheduling state and independently disabled cards; feedback alone changes none of these.
5. Same-request retry, concurrent revision conflicts, cross-learner isolation, rollback and backup/migration compatibility.
6. Sandbox UI: keyboard, narrow layout, visible status, answer retained, explicit undo/restore, no surprise topic/session change.
7. Replacement preview/publication: old/new mapping, affected count, retained source/history, atomic retry, no live publication during verification.

## Implementation boundary

This is a cross-cutting learning-eligibility change, so document it before adding schema or UI. Likely files are the integration map plus a shared lifecycle service/schema/migration, targeted tests and one existing question-feedback control. No new library, model route, hosted call or new grading policy is required. Review the first vertical slice contract before migrations; do not claim R5 complete from schema-only tests.

Baseline verification: `uv run pytest tests/test_areas_feedback.py tests/test_curriculum.py -q` passed 23 tests on 2026-10-08. This confirms existing compatibility only, not the proposed lifecycle. No UI changed; browser acceptance belongs to implementation.
