# Workspace execution evidence

The tutor previously treated an old notebook output as proof that edited code ran.
Prompt contract v11 now separates stale client output into historical_execution_output and
leaves the current output slot empty. An application-generated evidence statement distinguishes
stale output, unverified client output and no supplied output. None means independent execution
verification; an empty output does not prove that code was never run.

Static code explanation and conceptual help remain available. Replies for stale requests receive
a concise, readable/spoken limitation and a conditional instruction to rerun when execution results
are needed. The saved request retains the original code, output and stale flag. Saved metadata
records the evidence state; prompt versioning prevents exact replay of pre-change answers.

This is context and provenance handling, not a semantic verifier. The model can still be wrong,
and a correct disclosure does not cancel a contradictory generated claim. No model routing,
dependency, automatic notebook execution or competency evidence changes were made.

Validation: 48 targeted workspace, saved-answer, feedback and diagnostic tests; strict mypy over
186 app files; Ruff and format checks passed. Sanitized checkout independently passed 19 workspace
and saved-answer tests. Code and pedagogy reviews found no blockers/majors. Real-model results
are recorded separately using synthetic fixtures and disposable data; no broad quality pass follows
from the contract tests.

A fresh eight-case local-only synthetic run completed. The stale-output response itself now rejects
the old result as evidence for edited code and recommends a fresh run, consistent with the
deterministic disclosure. Previously passing missing-column/default-dropna cases remained correct.
Other cases still contain mathematical/teaching errors, and one exhausted literal-quote repairs.
This single run supports the targeted correction, not a broad model-quality or latency claim.
