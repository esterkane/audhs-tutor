# Grading evidence safeguards

Free-text answers must receive semantic review before keyword overlap can become competency evidence. Keywords remain routing diagnostics; only blank answers and explicit abstentions can resolve at the rubric level.
Use existing grader routes and structured criterion evidence. If no usable grade is available, return a retryable error before assessment, competency or FSRS writes; model-call audit records may still be written.
Keep prior confidence, learner-selected modes and answer drafts intact. No new schema, dependencies, model assignment, hosted route or UI controls.
Existing accessible error/retry behavior applies in every mode. No live learner history is rewritten.

## Acceptance / verification
- Passed: keyword lists, contradictions and short paraphrases require semantic grading (`test_orchestrator.py`). The three routing regressions failed before the fix.
- Passed: missing/extra/duplicate/unknown criterion rows and empty evidence are rejected; reordered valid rows are matched by identity.
- Passed: unavailable or uncertain grading returns HTTP 503 before assessment, competency or FSRS writes. Tests compare complete existing learner-state rows, including checkpoint data, before/after rejection.
- Passed: fake local-to-hosted escalation still produces a valid grade through existing budgeted routes; deterministic items and explicit abstentions retain their behavior.
- Passed: session and challenge error/retry component tests preserve answer/confidence; challenges now expose submission errors through an accessible alert. Listening submissions also catch errors while retaining their existing alert.
- Final verification: `UV_NO_SYNC=1 make lint` and `UV_NO_SYNC=1 make test`: 333 backend tests, 44 frontend tests. No live learner data or hosted calls used.

## Review fixes
Code review found two majors: positional relabeling could hide duplicate/missing criteria, and the challenge submission path lacked an error alert. Both fixed and covered by regression tests. Existing-state preservation and successful hosted escalation coverage added. Code re-review reports no remaining blockers/majors. Pedagogy review passed the applicable checks; its error-handler finding is fixed. No prompt files changed; no live-model accuracy evaluation is claimed.

## Limits
Model judgments can still be wrong; this slice prevents keyword-only bypass and structurally incomplete evidence, not all semantic errors. No learning-outcome or live-model accuracy claim.
