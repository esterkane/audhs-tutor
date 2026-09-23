# Assessment relevance verification

The curriculum prompt changed to v2. A local source-backed drafting trial still generated recommendation and course-cost trivia; deterministic validation must reject these suggestions. This is not evidence of universally reliable generation. Reviewed correction drafts remain unpublished.

The broader tutor suite used the local gemma3-12b route and an isolated database. Hosted-medium was unavailable, so no rubric scores or score deltas can be reported. The baseline used llama31-8b; this is not a controlled prompt-only comparison. Curriculum drafting is not exercised by these tutor cases.

| Case | Baseline hard checks | Current hard checks |
| --- | --- | --- |
| explain-qkv | Pass | Pass |
| hint-first-scaled-attention | Pass | Pass |
| kv-cache-recap | Pass | Fail: sentence limit |
| negated-full-solution | Pass | Fail: full solution, sentence limit |
| socratic-masking | Fail | Pass |

Overall: 3/5 versus baseline 4/5. No rubric regression threshold can be evaluated without judge scores. Private raw outputs remain outside Git.

Follow-up prompt experiments, not implemented in this slice:

1. Give the recap task a compact answer skeleton with a strict sentence budget.
2. Add contrastive examples distinguishing “give the solution” from “do not give the solution” to the hint task.
3. Add source-grounded positive and negative recommendation examples to drafting, then evaluate acceptance and false positives over several local runs.
