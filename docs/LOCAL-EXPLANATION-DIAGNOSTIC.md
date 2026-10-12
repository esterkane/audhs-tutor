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
