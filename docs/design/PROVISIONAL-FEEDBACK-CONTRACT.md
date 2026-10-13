# Provisional model feedback contract

Owner approved provisional feedback on 2026-10-13. This contract specifies implementation; enforcement is not active until the complete route/UI slice passes.

## Audited boundary
`orchestrator/grader.py` stages model GradeResult before `_apply_result` creates AssessmentAttempt, graded events, competency evidence and FSRS state. `schemas/grading.py:AttemptResult` requires score, review and mastery. `assessment_requests.py` validates completed and recovered responses as AttemptResult. `assessment_answers.py` saves assessment history from that shape. A presentation-only flag cannot enforce the approved separation.

## Outcome and storage
Add a learner-owned provisional feedback record separate from AssessmentAttempt. Store immutable request identity, session/assessment IDs, exact submitted answer, frozen question/rubric/content fingerprint, task-review binding, reported help/confidence, model route/prompt version, source restrictions/provenance, feedback, next step and original model output for private audit. No assessed score, correct verdict, calibration, competency or FSRS foreign key. Model criterion judgements are advisory output, never passed-check labels. A reviewed rubric does not certify this output.

Define an explicit provisional API outcome with feedback_id and policy_version, without score/correct/review/mastery fields. Keep historical AttemptResult readable. A typed outcome union must be adopted by submission, request lookup, staged continuation, saved feedback, revisions and all consumers together; never emulate an assessed result using zero values or fake review IDs. Provisional revisions reference their own feedback lineage; existing assessed revision history remains intact.

## Atomicity and deployment boundary
Reuse WorkspaceRequest identity/ownership/fingerprint and the existing claim lock. Commit provisional record, advisory event and completed response atomically; no learning evidence or schedule writes. Duplicate requests return that exact saved outcome. Source/content ownership and content-change guards still apply. No automatic re-inference for uncertain requests.

Policy is checked at application, not merely inference start: after deployment, any not-yet-committed model free-text result, including legacy grade_ready staging, becomes provisional. Already committed assessed outcomes replay unchanged as historical records. Persist the policy version with the new outcome. A request currently executing older code must be drained/stopped before deployment; do not run old and new workers concurrently against the live DB. An interrupted inference remains uncertain, never silently restarted. Test legacy prepared/grade_ready records explicitly. This chooses conservative handling within the owner's approved future-feedback policy, without rewriting historical evidence.

Only model-checked free-text outcomes change. Deterministic MCQ/cloze/code paths and explicit learner self-report remain separate. Audit every local/hosted free-text branch including challenge/listening and mixed rubric/model routes; do not gate solely on the surface name. Model errors remain errors with preserved work, never provisional fabricated feedback or failed assessed attempts. No new hosted routing, verification model or paid calls.

## Learner flow
Display “Model feedback — not an assessed result” with a saved receipt. Keep answer, rubric, explanation, follow-up chat, revision, optional audio, Stop and Continue available. No score, passed badge, confidence calibration or mastery delta for this outcome. Continue must not require a pass or create an assessed event. Progress may show an explicitly provisional activity entry but cannot qualify it as task-specific assessed evidence.

Preserve learner ownership across read/search/revision endpoints and citations. Include records in private/learner backup and wipe paths under existing source restrictions; do not export restricted material to hosted providers or sanitized publication. Reuse existing saved-answer access contracts rather than creating a second unrestricted cache.

## Delivery and acceptance
1. Add strict outcome schema and separate storage/migration, ownership and backup/wipe tests. No runtime routing switch yet.
2. Integrate atomic persistence and recovery with new union; prove no new AssessmentAttempt/competency/evidence/review/memory/pass writes for provisional outcomes. Test duplicate/concurrent submission, commit-response loss, staged legacy recovery, changed content, foreign learner and revisions. Deterministic/historical regressions remain green.
3. Integrate all learner surfaces and saved feedback/help; browser checks cover reload, double-submit, slow/error, Stop, revision and Continue at desktop/narrow sizes with keyboard and visual review. Only then deploy the policy and regenerate API types.
4. Independent model-quality evaluation remains a separate future gate; synthetic contract tests establish isolation, not accuracy. No automatic promotion back to assessed grading.
