# R5 — eligibility at assessment and recovery boundaries

Story: a suspended question cannot be graded from an old link or pending submission; completed results remain historical evidence. A restore requires reviewing a fresh view before a new submission.
Learner state/revision becomes part of assessment content identity when an explicit decision exists. Missing state retains the old active fingerprint, preserving legacy pending recovery compatibility.
No grading/rubric/mastery policy, API response schema, model route or learning evidence is changed. This guards existing submission/recovery paths; selector/generation and visible suspend/restore action remain pending. No live migration or content mutation.

## Implementation and problem evidence

Baseline new tests: three failed (direct refresh/new claim, restore token, prepared continuation), two passed (completed replay and saved-grade rejection via the earlier review guard). The new checks move rejection before grading/claim/model activity and explicitly bind recovery to learner eligibility.

`assessment_content` snapshots optionally join learner state/revision; all production view/grading/recovery call sites now supply learner context. Absence leaves the previous snapshot shape unchanged. Read-only/test callers may inspect shared content without learner context; new grading always obtains context from the owned session. Shared content inspection is not permission to grade.

New submissions, direct views, prepared continuation and finishing a staged grade require eligible content. The commit-time SQLite guard rechecks both content and eligibility revision. A suspend→restore during inference is still a version change and cannot create evidence. Durable staged grades stay available for diagnosis but cannot update progress from an earlier revision. Completed replay occurs before new-action validation and remains intact.

## Remaining work

Question selectors and generated-item reuse still need eligibility filtering before the feature is exposed. Exercise hints/solutions, linked check availability and listening validation need the same deliberate eligibility treatment with the selector slice; this change does not claim those flows are complete. No UI changed, so responsive/keyboard/visual suspension-control acceptance remains pending. No live database changes or API suspension route was added.

## Verification — 2026-10-08

Full backend961 passed (three existing warnings), Ruff and strict mypy206 pass. Eight new tests cover direct refresh/new claim, restore token, completed replay, prepared continuation, staged-grade finishing, direct kernel grading, in-flight suspend→restore and learner-isolated snapshots. In-flight changes retain the staged result but write no attempt or competency evidence. Bounded code/learning-semantics review found no blockers or majors. No frontend changed; its pending UI gates are not claimed. Logs: /tmp/question-assessment-{before,targeted,tests,full,ruff,mypy}.log.
