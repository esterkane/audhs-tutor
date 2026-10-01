# Local formative-feedback candidate diagnostic

## Purpose and method

Investigate the observed attribution error before changing model routing. Extend `scripts/eval_workspace_modes.py` with explicit installed-local model selection, a pinned gateway router with no fallback, exact synthetic request snapshots and a correct-answer control. The existing loopback, hosted-credentials-off and disposable-database boundaries remain. Qwen2.5:3b is registered only in the disposable database after confirming the tag is already installed; no download or live registry edit occurs.

Ran four identical cases each for installed Gemma3 12B, Llama3.1 8B and Qwen2.5 3B. All twelve calls completed and record the actual registry ID. Cases: Socratic opening, wrong arithmetic feedback, one hint, and correct arithmetic feedback. Model calls use the normal accounting gateway inside the disposable evaluation database. These are one sample per case, not a comparative benchmark or automated teaching grade.

Raw synthetic inputs/outputs are in `evals/results/answer-memory/modes-{gemma3,llama31,qwen25}-initial.json`.

## Manual review against known arithmetic and requested behavior

| Candidate | Wrong-claim feedback (`30/50 = 0.9`) | Hint-only instruction | Correct-claim control |
|---|---|---|---|
| Gemma3 12B | Computes0.6 but falsely says it was the learner's correct calculation; internal tags leak | Adds a new question | Correctly recognizes0.6/60%, but emits internal tags |
| Llama3.1 8B | Repeats the claim and describes division, but does not give the requested correction | Adds a question | Correctly simplifies30/50 to3/5; no explicit verdict or percentage |
| Qwen2.5 3B | Incorrectly endorses0.9/90% | Switches to removed-row count and asks two questions | Correctly recognizes0.6/60% |

No candidate satisfies all four cases. Opening questions also vary in relevance and ratio wording. There is no supported winner or authorization-by-benchmark to change live routing. Existing explicit/Socratic request integrity remains implemented; formative correctness remains OPEN. Independent review agrees that these samples expose failures rather than establish overall model quality.

## Next bounded implementation

1. Bind formative feedback to a distinct, exact current learner-answer field, separated from previous assistant text and action instructions. Preserve it in the saved immutable request and reuse key.
2. Validate quoted claims against that exact text before attributing a statement to the learner. A failed attribution must not be presented as checked feedback.
3. Add deterministic checks only for clearly supported small calculations, with a visible scope statement: checking an expression does not validate its application, fairness, code execution or the whole answer. Unsupported/ambiguous claims remain unverified.
4. Re-run wrong and correct controls, changed answers, hint-only/Socratic/direct modes, ambiguous or absent answers, prompt injection and incomplete output. Preserve ordinary explanation/help if checking fails; never award mastery from this feature.
5. Reassess installed-local adequacy only after binding/checking defects are addressed. Any hosted comparison must remain task-specific and use existing budget/accounting; no blanket route switch.

## Verification

Twelve actual local calls completed through pinned gateways; no downloads or live routing changes. Repository lint/types pass. Independent review found no safety or attribution blockers in the diagnostic. No application runtime/schema/UI code changed in this slice, so existing477backend and browser evidence is not represented as a new run.
