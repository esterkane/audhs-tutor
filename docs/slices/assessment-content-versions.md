# Assessment content versions (R3)

## Behavior

Assessment submissions carry an opaque token for the question the learner saw, including hidden expected answers, assessment kind/skill and the complete rubric. A changed prompt, expected answer or rubric requires explicitly refreshing the question. The original question and answer are archived in browser session storage after refresh until explicitly dismissed; a storage failure retains the original pending record. Written answers and code remain available; multiple-choice selections must be chosen again because option positions can change.

The displayed question stays fixed while the learner answers. Refresh reads the same item instead of generating a replacement. An earlier submission from another activity cannot be dismissed by refreshing the current activity. Code refresh discards old execution/check results and stops the old worker; source edits remain.

Completed request identities replay their original result, even after content changes. Legacy versionless completed requests retain their original payload fingerprint. New HTTP submissions without a version fail closed. Old pending browser records remain readable for result lookup; they are not silently assigned today's version.

If content changes during inference, no learning evidence is committed. The request remains unresolved and is not automatically submitted again. Resolving such interrupted claims is still a separate R3 task; model work that already happened must not be repeated on an assumption.

## Ownership and limits

Tokens use a process-bound HMAC over one joined server snapshot. Hidden answers are not published as guessable hashes. A backend restart invalidates displayed tokens; explicit refresh obtains a new token, while durable completed replay remains valid. This matches the current single-process local deployment; a multi-worker deployment would need a shared protected signer before use.

Grading uses detached copies of the question/rubric. A short SQLite write lock protects the final content check and atomic learning writes. Model inference remains outside that lock. No schema migration or model-route change is required. Internal direct grader callers remain compatible, while all HTTP assessment/challenge submissions require version evidence. Review-rating content revisions remain outstanding.

## Verification

Verified 2026-10-03: full backend 748 tests, frontend 391 tests, lint/types and production build passed. Four Chromium journeys passed (desktop/narrow stale refresh and lost-response replay). Independent code and pedagogy reviews identified and verified fixes for claim serialization, wrong-activity recovery, old code-worker disposal and durable original-answer retention. The first broad backend rerun exposed a review concurrency regression; limiting the extra claim lock to content-validated assessments fixed it, and the complete suite passed afterward. The private synthetic baseline reproduced acceptance of an answer after its displayed question changed. Regression coverage includes pre-submission prompt/key/rubric edits, edits during inference, legacy replay, explicit refresh, recovery persistence, and different-activity safeguards. Browser journeys exercise stale rejection and lost-response replay at desktop and narrow sizes against a disposable database. No live curriculum or learner history is changed by these tests.
