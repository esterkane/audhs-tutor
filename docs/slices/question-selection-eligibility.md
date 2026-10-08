# R5 — question selection and canonical reuse

Story: excluding a question stops future selection without deleting history or silently regenerating its canonical content. An excluded linked check does not remove the code workspace.
No automatic suspension, changed grading criteria or model route. State remains learner-scoped. No mutation API/UI action is exposed yet; explicit controls, status/restore discovery and complete browser acceptance remain next.

## Baseline and change

All five initial regression scenarios failed before this integration: ordinary selection; excluded code hint/solution access; linked-check visibility; challenge reuse; listening reuse/validation. Existing submission/review guards already protect evidence writes.

- Ordinary assessment selection excludes ineligible questions and returns none when exhausted; attempts/history are untouched.
- Session-stop recall ignores unavailable/inactive existing cards when determining whether to create an eligible recall card. If all questions are excluded it creates nothing. Existing schedules are retained.
- Shared catalog code/listening lookup deliberately retains canonical identity. A suspended canonical question raises an explicit unavailable response before reuse, rather than pretending it is missing and creating a clone. Listening rechecks after concurrent deduplication; validation locks before status/payload read.
- Challenge reuse selects eligible unattempted questions. If none remain and an excluded question exists in that skill/mode, implicit generation is blocked before retrieval/model use. Another activity or explicit restore is available; reviewed replacement is future work. This intentionally does not claim semantic detection of generated paraphrases.
- Code hints/solutions enforce eligibility. A suspended linked explain-back check has no actionable ID/token and shows an unavailable message; starter code, runnable checks and code grading remain available. No unrelated UI controls are removed.

## Remaining acceptance

Expose explicit suspend/restore with revision and retry identity, impact preview, status explanation and recovery from stale actions; verify browser keyboard/narrow flows and live migration readiness first. Replacement preview/publication and semantic quality review remain open. Catalog helpers remain shared content-identity functions, not learner selectors; their API view/guards enforce eligibility. Learner-private state must never be baked into shared course content.

## Verification — 2026-10-08

All five baseline scenarios failed before implementation. Final21 focused selection/exercise/listening tests and full backend967 passed (three existing warnings). Ruff and strict mypy206 pass. Bounded code/learning review found no blockers or majors. Six new tests cover exhaustion, canonical no-clone reuse, hint/solution exclusion, linked-check workspace preservation, challenge generation blocking, listening validation and session-end recall selection. No hosted/model work is required for excluded generation tests. Logs: /tmp/question-selection-{before,tests,full,ruff,mypy}.log. No frontend code/schema changed; integrated visual/browser checks remain required with the new controls.
