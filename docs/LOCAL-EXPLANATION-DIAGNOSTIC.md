# Local explanation diagnostic — 2026-10-12

## Scope

Three newly authored synthetic workspace requests through current playground.respond
and the existing eval_local_runtime harness, pinned to installed gemma3-12b. Disposable
SQLite database, only loopback Ollama provider, hosted keys empty, budget zero, no
production routing change. This is a workspace explanation sample, not the main lesson
flow, an accuracy benchmark or a learning-outcome result. Follow-ups use the same
fixed, correct synthetic history, not the first generated reply.

Raw evidence: ../evals/results/explanation-local-20261012.json (relative to docs).
It contains exact requests, model-visible messages, hashes, replies and attempt timing.
The temporary adapter is /tmp/audhs-explanation-sample.py; it overrides only the
harness cases for this run. No production prompt was changed or tuned against these
cases. The raw artifact is retained unchanged; judgements below are manual inspection
by the implementing assistant, not independent review.

## Findings

| Request | Observed response | Manual assessment |
| --- | --- | --- |
| Correct the belief that append returns the modified list | Correctly predicts values=[2,4,6], result=None; distinguishes mutation and return | Factual core correct. “Doesn't return anything” immediately followed by “returns None” is avoidably imprecise for a beginner. “You're close” adds little specific feedback. |
| I do not understand; explain simply one step at a time | Repeats mutation/return explanation in one compact paragraph | Partial. Relevant and correct, but does not demonstrate a simpler representation or staged explanation. This is the actionable pedagogy gap. |
| More detail; contrast append and concatenation | Correct comparison and two code examples, followed by a relevant check question | Meets this narrow request. The check follows direct explanation; it does not replace it with a questioning loop. |

All three begin with a literal “(explanation)” marker; this is raw model text,
not an application-added UI label. No observed claim of having run code or inspected
real course sources. The predictions were separately checked with handwritten local
Python assertions; generated code was not executed. No new learning evidence or
mastery claim was created in the owner's database.

## Timing and cost boundary

Full respond/result lookup:12.705s,3.194s,7.115s. Each made one local explain_simple
model attempt with reported cost0. These are total response times, not first-token
latencies; three ordered calls cannot establish a median/p95 production benchmark or
attribute the first delay to model loading. No paid-provider fallback occurred.

## Next bounded work

Before changing prompts, reproduce the simplification weakness on at least one
contrasting concept and inspect current explicit/explanation controls. Define a small
separate validation set for any prompt change: preserve factual caveats, show a clear
first step and concrete example, avoid mode labels, and do not force Socratic mode.
Compare current versus proposed behavior without changing model routing or shrinking
useful context. A single successful rewrite cannot close the gap.

G1 remains open for main-lesson repeated wrong answers, richer held-out material,
source ambiguity and independently reviewed teaching quality. Human comprehension,
physical audio, delayed transfer and whole-platform semantic accuracy remain unverified.


## Contrasting concept and rejected prompt candidate

Two more current-prompt samples used synthetic group missingness counts. The model
correctly computed A=20/80=25% and B=10/20=50%, but again returned paragraphs rather
than the requested steps. The fairness answer retained uncertainty but introduced
hypothetical missingness causes and ended with the technical phrase “mechanism of
missingness.” These are not established facts about any real learner or dataset.
Raw evidence: ../evals/results/explanation-contrast-20261012.json.

A temporary, non-production prompt addition requested familiar language, concrete
starting points, numbered steps when requested, preserved uncertainty and no mode
labels. It was tested once on four cases: group counts, fairness limits, list mutation
and a separate mean-of2/4/9 example. It was NOT adopted:

- Counts and list mutation gained numbered steps; arithmetic stayed correct.
- Two of four still emitted “(explanation)” despite the prohibition.
- List explanation added an unrequested question in explicit mode. This is a mode
  adherence failure, not evidence of helpful Socratic teaching.
- Fairness response introduced MCAR/MAR/MNAR without explaining them, making the
  request for simplicity less usable. Its possible causal story remained unverified.
- Mean answer correctly gave5 but omitted the requested minutes unit in its result.

Raw evidence: ../evals/results/explanation-candidate-20261012.json. This artifact's
runtime_prompt_version identifies the underlying unchanged runtime; the experiment
appended system text in a temporary adapter. It MUST NOT be treated as production
prompt evidence. Exact trial text is present in gateway_requests.messages. Both
follow-ups used supplied fixed history; this is not a continuous learner conversation.
Candidate total response times10.352/4.382/7.304/5.563s; baseline contrast6.015/3.725s.
No statistical latency comparison is justified. All six calls were local Ollama,
reported0cost; no production setting, prompt or model route changed.

Stopping decision: no further wording iterations in this diagnostic. Before a runtime
change, inspect the existing alternative-representation path and its mode contract.
Evaluate a bounded design that preserves literalness, uncertainty and explicit-mode
control alongside step structure; do not add a second inference call or regex-strip
questions as a substitute. G1 remains open. These judgements are manual assistant
review, not independent pedagogy review or human comprehension evidence.
