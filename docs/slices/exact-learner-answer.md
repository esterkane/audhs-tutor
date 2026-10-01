# Exact learner answer in workspace feedback

Status: implemented and verified; model accuracy gate remains open.

Give feedback against the current submitted answer, separately from run output and historical conversation. Preserve the full submitted text (up to 8,000 characters); reject oversized submissions without clearing work. Socratic answer submission supplies that response; starting a question or requesting a Socratic hint does not submit an unsent draft. Persist the immutable snapshot, show it in saved-answer details, and exclude different answers from historical reuse. No new learning evidence, mastery, grading, model routing, sound or mode adaptation. Existing keyboard controls, stop and stale-response protection remain.

Baseline: StudyTutor placed task answers in the output field and silently cut them at 1,950 characters. The request schema had no dedicated answer field. Local trials also showed misattribution and arithmetic errors; this binding change alone cannot establish model correctness.

Remaining after binding: validate attributed quotations, scoped deterministic arithmetic checks and a broader local quality evaluation. No automatic quality gate is passed by structural tests.


## Verification

- Reproduced absent-field failure before implementation with a regression test.
- Full backend: 479 passed; full frontend: 227 passed. After review fixes: 17 focused backend and 29 frontend tests passed; final lint/types passed.
- Production build passed (existing chunk-size warning). Two isolated Chromium notebook/conversation journeys passed at 1280px and 390px, checking actual submitted request binding.
- Tests cover full 7,900+ character answer preservation, oversized rejection and retained work, changed-answer replay/retrieval exclusion, null unsent Socratic hint/start, exact saved detail and follow-up history, untrusted boundary escaping, no assessment/competency write. Existing stop/error/stale-answer regressions remain green.
- Independent code/pedagogy review fixed loss of original learner answers in saved follow-ups and the outdated truncation notice; re-review found no remaining findings.

## Local quality evidence

`evals/results/answer-memory/answer-binding-v7.json` records four synthetic, pinned Gemma trials against a disposable database, no hosted budget or fallback. The hint stayed on the existing question and supplied no solution. The incorrect-answer case explicitly endorsed `30/50 = 0.9`; the correct-answer case invented a fraction-versus-percentage objection. These are failures, not a teaching-quality pass. Binding alone does not validate arithmetic, quotations, interpretation or the whole answer. Routing is unchanged. Next: scoped deterministic checks and attribution checks, with broader local re-evaluation.

## Boundaries

The current task answer is complete within the 8,000-character API limit; material/code/output retain separately disclosed bounds. Socratic chat retains its existing 1,700-character UI bound to fit the action wrapper. Starting or hinting does not submit a new answer. Historical follow-up supplies the immediate parent's answer under historical context, not as a new submission; it does not recursively expand the whole conversation. No schema migration, dependency, paid call, live assessment or mastery update.
