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


## Representation boundary inspection — 2026-10-12

Current source inspection identifies a concrete instruction conflict, not simply
a missing request for numbered steps. `prompts/_base/pedagogy.v2.md` directs every
concept explanation to choose a representation and print its name first. Both
workspace task prompts direct literal explanation with no representation prefix
unless requested. `playground.messages` concatenates these into the same system
message. The diagnostic label failures are therefore consistent with conflicting
instructions; this does not prove that conflict caused every observed failure.
The base also invites predictions when helpful, whereas explicit workspace mode
forbids unsolicited questions. Those boundaries need reconciliation before another
local sample, rather than adding a third competing instruction.

The existing alternative-representation service is a different operation:

- `orchestrator/representations.py` renders a LearningObject concept/goal with
  skill-scoped retrieval. Its cache is keyed by object and representation kind;
  it does not receive the workspace's exact code, answer or selected step.
- `kernel/representations.py` exposes seven kinds, including mastery-gated
  problem-first. It has no shorter/smaller-steps kind.
- `routes/Session.tsx` explicitly requests these alternatives and retains the
  previous explanation. `representation.v1.md` explicitly asks for a kind label.
- `programs/StudyTutor.tsx` instead sends adaptation requests through playground
  with the same target, work snapshot and bounded history. That boundary should
  remain: redirecting it to concept-only rendering would lose relevant context,
  and caching personalized adaptations by object/kind would be insufficient.

### Next bounded implementation proposal

Version the shared base policy to make literal explanation the default and defer
representation naming to an explicitly selected task contract. Make optional
predictions conditional on the chosen questioning mode; preserve the existing
explicit full-solution contract separately. Retain the dedicated representation
task, its kinds, cache, source grounding and mastery gate. Do not change learning
logic, model routing, schemas, UI controls or add inference calls.

Likely files: a new versioned base prompt, `orchestrator/prompts.py`, focused prompt
composition tests, and this diagnostic record. Inspect all base-policy consumers
and their version/cache identities before editing; additional affected prompt
versions must be explicit rather than silently reusing old cache identities.

Acceptance: composition tests must cover workspace explicit/Socratic requests and
explicit representation requests. One bounded local comparison must test labels,
unrequested questions, simple step structure, uncertainty and units, with a held-out
concept. Stop if improvements only affect labels or another contract regresses;
do not claim the broader teaching-quality gap solved. Obtain code/pedagogy review
before adopting a production change. No runtime changes or extra model calls were
made during this inspection; browser/keyboard/reflow evidence is unchanged.


## Shared-base trial — not adopted

A temporary in-process replacement of the base representation paragraph made
literal explanation the default and deferred labels to explicit task contracts.
A second replacement restricted optional predictions to Socratic mode, preserving
the separate full-solution check. No task prompt, production file or model route
changed. Exact composed messages are in
`evals/results/explanation-base-conflict-20261012.json`; its runtime version identifies
the unchanged underlying runtime, NOT the temporary policy.

Six completed local gemma3:12b calls, zero reported paid cost:

| Case | Observation | Total reply time |
| --- | --- | --- |
| Counts | Correct 25%/50%, numbered comparison; unwanted question | 12.428s |
| Fairness | Retains uncertainty but MCAR/MAR/MNAR still increases complexity | 3.825s |
| List | Correct numbered trace and None; unwanted clarification question | 6.240s |
| Mean | Correct 5 minutes, explanation in paragraphs | 4.893s |
| Socratic control | One relevant question, no full solution | 2.095s |
| Requested analogy | Switches to time rates instead of supplied group proportions; does not connect back to data | 4.286s |

Representation prefixes disappeared in this sample, but fake-looking
`[general guidance]` labels remain. Literal arithmetic is correct; teaching/mode
contract adherence is still insufficient. Reject the candidate under the stated
stopping criterion. These single synthetic samples are manual diagnostic evidence,
not causal proof, statistical comparisons, a representation-endpoint test or human
comprehension validation. No UI change: keyboard/reflow evidence is unchanged.

Consumer inspection also found separate version metadata for workspace, grader,
area drafting and curriculum drafting; a future shared-base adoption needs to
account for those consumers, not just bump the lesson prompt version.

Stop further wording experiments in this diagnostic. Preserve this gap in G1.
The next useful quality step is a fixed, independently reviewed teaching-contract
evaluation spanning these failures and untouched cases before comparing capable
installed local models; do not weaken quality or enable paid routing automatically.
Continue the independent integrated-acceptance queue while that gate remains open.


## Reusable teaching contract suite

The existing local diagnostic now accepts `--suite teaching`. Eight fixed cases
cover count/rate steps, fairness uncertainty, list mutation after prior explanation,
mean with units, chosen Socratic mode, requested analogy, borrowed/remaining
fractions and uncertain extrapolation. Each has explicit manual review criteria
and a separate synthetic target; saved-answer reuse is off. The existing manifest
hashes requests and criteria, so changed fixtures cannot silently claim comparability.

Run only when testing a defined candidate, from the repository root:

```sh
uv run --project backend python scripts/eval_local_runtime.py --suite teaching --model gemma3-12b --out /tmp/teaching-candidate.json
```

Use a fresh output path. Existing loopback-only, no-hosted-key, no-fallback and
disposable-database restrictions apply. This suite does not call the main lesson
representation endpoint, run learner code or exercise production routing. Compare
identical fixture hashes; inspect exact source/work fidelity, mode adherence and
clarity before latency. Do not average away factual/mode failures or use a keyword
match as semantic approval. Record each case as met/partial/failed with quoted
evidence; no automated semantic pass is implemented.

Independent code/pedagogy review found no blockers/majors; noted limited domain
breadth (mostly arithmetic) and only one prior-explanation follow-up. The two transfer
examples are newly authored, not permanently held-out once used for tuning. These
limits preclude a broad teaching or learning-outcome claim. Typed history replaced
a raw fixture dictionary to eliminate serialization warnings. All17 offline harness
tests, targeted Ruff and CLI help pass. No additional model run, runtime prompt, UI,
learning-state or routing change; visual/keyboard/build checks are unchanged.


## Fixed-suite model comparison — no routing change

Current unchanged production prompts were sampled once per case with installed
gemma3:12b and gemma3:27b, sequentially, through the local-only harness. Both
completed all eight cases with identical fixture hash
`1f1827e6bedbada971f5f622c3115c0e3b5496e91e6af5d82ae67501fef2f718`.
All16 calls used Ollama and reported zero paid cost. Raw artifacts:
`evals/results/teaching-12b-fixed-20261012.json` and
`evals/results/teaching-27b-fixed-20261012.json`.

Manual evidence review (not independent grading or human comprehension):

| Case | 12b | 27b |
| --- | --- | --- |
| Counts | Correct rates; unwanted representation prefix | Correct rates and ordered prose |
| Fairness | Failed: changes80 total rows into80 missing incomes | Failed: says observed incomes will reveal whether missingness depends on income; not established from observed values alone |
| List | Correct mutation/None and sequential explanation; prefix remains | Correct outputs but ends with an unwanted question asking for the outputs it just supplied |
| Mean | Correct5 minutes | Correct5 minutes, then unsolicited question |
| Socratic | One relevant question; prefix remains | One relevant question |
| Analogy | Arithmetic correct but says proportions are misleading; lacks a clear analogy limit | Failed: cake needs100/has80 but calls80 missing; analogy denominator differs from supplied80-row group |
| Fractions | Fake[1] sources, incomplete final calculation; runtime warning correctly appears | Correct3/12 and9/12 but falsely attributes a prior calculation error to learner; unsimplified results |
| Prediction | Correctly rejects proof, retains uncertainty; prefix remains | Correctly rejects proof and suggests more evidence; generic next-action prompt |

The 27b analogy later gives correct original rates; that does not repair its
contradictory example. Accurate prediction of some outputs does not offset invented
learner claims or factual errors in other cases. Neither sample closes G1.

Median total respond latency was4.2585s (12b) and10.7845s (27b). These are completed
reply times, not first-token latency; one sequential run per model includes model
loading/warmth differences and does not establish a stable latency distribution.
No quality-and-speed win supports switching. Leave routing unchanged; no further
model/prompt sweep follows this result. Main lesson representation, grounded sources,
long conversations and actual learner comprehension remain outside this suite.

Next quality work should address the observed source/work fidelity and false
learner attribution with targeted contracts and review, rather than adopting a
larger model or treating citation warnings as correctness verification.


## Current chat baseline, 2026-10-12

`evals/results/teaching-8b-fixed-20261012.json`: eight completed synthetic cases,
local llama31-8b, zero hosted calls. Median total response 3.555s, one sample/case;
not TTFT or a statistical speed comparison. Same fixed teaching fixture as12b/27b.

Manual review rejects a quality pass: counts_steps omits both requested percentages
and incorrectly says each B row has ten missing incomes. requested_analogy changes
A's denominator from80 to100 and confuses sample membership with missingness.
list_steps explains mutation/None but omits the explicit output list and adds an
unrequested understanding question. transfer_fraction gets1/4 and3/4 but omits the
requested percentage forms and9/12. fairness_uncertainty correctly avoids a fairness
conclusion (its suggested inspection largely repeats available evidence); mean_units
and transfer_prediction are correct for these fixtures. socratic_choice asks one
focused question. These are diagnostic observations, not learner outcome evidence.
No routing/prompt change. The completed Glimmer comparison follows below; parameter
count alone is not quality evidence.


## Glimmer fixed-suite result, 2026-10-12

Artifact: `evals/results/teaching-glimmer-fixed-20261012.json`. Same eight-case
fixture hash, app prompt and 900-token limit as the baselines. Five replies completed;
three failed (`list_steps`, `requested_analogy`, `transfer_fraction`). All eight
attempts used local Ollama, recorded cost $0, with hosted fallback disabled.
Median time across all eight attempts, including failures: **39.704s**. Median of
only the five completed replies: **33.134s**. Neither is first-token latency.
One ordered run with mixed loading/cache conditions cannot establish a stable
performance distribution. It does establish that this configuration is unsuitable
for the current interactive response-time requirement.

Manual review: counts correctly retains both denominators and computes25%/50%,
though its next step redundantly asks the learner to repeat them. Mean gives the
correct calculation and units. Socratic mode asks one focused denominator question.
Prediction distinguishes an assumed extrapolation from proof. Fairness correctly
rejects inference from missingness counts alone and requests group performance;
this is not a complete definition or assessment of fairness. No visible answer
exists for the three failed cases, so they cannot receive a teaching-quality pass.
The raw artifact retains `semantic_review: not_reviewed`; this paragraph records
human-readable inspection separately, without rewriting the original measurements.

Each failure recorded `invalid_output`,900 output tokens and AppError. The artifact
lacks provider finish reasons and hidden reasoning, so token exhaustion is a
hypothesis, not a proven cause. Do not silently increase limits or change reasoning
settings and merge those results into this run. No production routing promotion.
A separate, bounded transport/reasoning investigation would precede another trial;
no additional model sweep is needed to reach the present decision.
