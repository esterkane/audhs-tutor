# Local lesson grounding diagnostic

2026-10-04. Synthetic single-run evidence, not a quality pass or a learning-outcome claim.

## Method

scripts/eval_lesson_grounding.py reuses the actual playground respond path and existing local-only pinned gateway. Seven cases cover supported/conflicting/irrelevant/empty passages, wrong reasoning, stale output and starter code. A temporary database and isolated SQLite retrieval with synthetic embeddings keep owner data and production retrieval out of the sample. Reports record requests, exact model messages, supplied sources, persisted metadata, timing and model attempts. Artifact creation is exclusive; interruption is recorded. Hosted credentials are removed and loopback Ollama is required. No generated code is executed.

The real local sample used llama31-8b:7/7 completed, all attempts Ollama, reported API cost0. Median observed per-case runtime2.739s, range1.403–10.620s; one run and possible cold-start effects make this unsuitable as a latency benchmark. Raw output remains in the private archive; production routing was not tested or changed.

## Independent semantic review

| Case | Verdict | Concrete issue |
|---|---|---|
| Supported | Partial | Correct11 and supporting citation, but wrongly attributes multiplication to sum and describes zip as a list. |
| Conflicting | Partial | Notices disagreement but does not resolve the arithmetic. |
| Irrelevant | Partial | Avoids citing irrelevant passages, but does not disclose their irrelevance or compute the concrete result. |
| Empty | Partial | Valid formula but no concrete11 or model-level acknowledgment of absent evidence; UI source note does disclose absence. |
| Wrong answer | Partial | Corrects0.9 to0.6 and rejects90%, but never supplies60%. |
| Stale output | Partial | Correctly refuses old output as proof, but omits static reasoning and exposes an internal field name. |
| Starter | Fail | Calls NumPy standard-library and solves the task rather than leaving meaningful learner work. |

Result:0 full passes,6 partials,1 failure under the declared criteria plus factual teaching accuracy. Citation formatting success alone is not claim support. Model-generated code remains unverified.

## Application fix discovered by the sample

The source disclosure misclassified vector literals such as [1,2] as unsupported references. Grounded prompts specify standalone numeric markers; the guard now limits that check to single [n] markers and still warns for out-of-range markers. Composite brackets remain ambiguous and are not validated, rather than being falsely labeled incorrect. Source-free disclosure behavior is unchanged. Original raw evaluation output is retained unchanged; this correction was verified by regressions, not a new inference run.

## Verification and next work

Diagnostic fixture test verifies all seven validated lesson origins, isolated source texts and retained chunk records. Existing runtime diagnostic and source/provenance regressions pass:30 tests in each checkout. Script Ruff passes; independent code review found no blockers/majors. No screen layout or interaction changed; browser/keyboard/responsive checks are not applicable to the diagnostic or text-classifier delta.

Next bounded changes: strengthen explicit grounded reasoning instructions (calculation despite conflict, relevance/absence disclosure, static versus executed results) and rerun these exact cases. Starter requests need a distinct validated contract for standard-library imports and unfinished learner work; do not present prompt instructions as enforcement. Preserve local routing until an evaluated task-specific alternative is warranted. C3 quality/owner acceptance and broader C4/C5 remain open.
