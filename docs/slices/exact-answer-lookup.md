# Exact saved-answer lookup independent of relevance ranking

When the learner opts to reuse an identical workspace request, newer related conversations must not hide the earlier exact answer. Match the complete supplied request before the bounded source-check candidate limit; punctuation-only questions must also be reusable. Keep owner, task/work, feedback, prompt-version and source checks unchanged. No events, evidence, UI or routing change; opening history still makes no model call.

Reproduction: two regression tests fail before the fix: three newer answers with different conversation history displace the exact match, and a punctuation-only question is rejected by FTS tokenization. Exact lookup now applies full request-field SQL filters before its 20-candidate limit, with final Python structural equality and source checks. It no longer depends on the two relevance-ranked excerpts.

Verification in progress. Exact replay remains opt-in and does not certify external files/datasets or model correctness. Nested context/history are generated from the typed request schema; legacy records missing fields conservatively miss. Source revalidation remains bounded to 20 otherwise exact matches.

Verification complete: 476 backend tests and lint/types pass. Three regressions cover displaced exact matches, punctuation-only requests, Unicode/reordered nested keys and missing/wrong-type fields. Existing route test asserts zero additional model calls and no duplicate saved record on opt-in replay. Independent code/pedagogy review found no blockers/majors. No UI/schema change; previous interface verification remains applicable.

## Buffered local diagnostic

`scripts/bench_answer_reuse.py` exercises production workspace orchestration on synthetic data in disposable SQLite, with loopback Ollama and hosted credentials disabled. Raw result: `evals/results/answer-memory/buffered-reuse-initial.json`.

| Case | Complete response | Model calls | Reused |
|---|---:|---:|---|
| Initial generation | 13,581 ms | 1 | No |
| Identical opt-in replay | 14 ms | 0 | Yes |
| Changed supplied material | 3,969 ms | 1 | No |
| Explicit fresh answer | 5,052 ms | 2 (query embedding + generation) | No |

Indexing took398ms separately and is excluded from response timing. This is a single ordered sample, with model warm-up and output-length differences; it is not a statistical benchmark or streaming first-token measurement. It demonstrates one avoided generation on an exact repeat. It does not establish semantic speedup or teaching accuracy. Responses omit the supplied percentages, and the changed-material response does not calculate40/50; quality work remains open. Reusing an answer also reuses its limitations.
