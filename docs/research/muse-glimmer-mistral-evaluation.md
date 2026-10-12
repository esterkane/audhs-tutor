# Muse Glimmer and Mistral Large 4 evaluation

Assessment date: 2026-10-12. Status: research complete; candidate execution and integration NOT approved or performed.

## Decision

Evaluate Glimmer locally first, after approval for its approximately 19 GB download. Do not replace existing routing yet. Mistral is an optional, explicitly budgeted comparison candidate, not a default tutor. Neither has app-specific quality evidence. Adding an agent framework, database or inference service is unnecessary.

## Existing architecture and reusable boundaries

Reviewed AGENTS/CLAUDE, README, architecture, roadmap and ADRs 0001, 0010 and 0014, together with registry, providers, gateway, budgets, orchestration and evaluation code.

- `backend/app/models_ai/provider.py`: existing ModelProvider complete/stream contract and typed structured results. Message currently contains text only; native image/tool conversation transport is not automatically supported because a model advertises those capabilities.
- `models_ai/ollama.py`, registry and `routing_profiles.yaml`: reuse local serving, readiness and assignment machinery. Candidate registration can be isolated to a disposable evaluation database. Do not seed or change live assignments.
- `models_ai/gateway.py` and `budget.py`: retain routing, attempt accounting, reservations, cancellation and structured-repair behavior. HOSTED_PROVIDERS currently lists Anthropic and OpenAI only. Mistral needs an explicit adapter, configuration/readiness and hosted classification before any request; an OpenAI-shaped API alone is insufficient.
- ModelSpec prices input/output; ProviderResult carries cached tokens, first-token timing and reported cost. Cached/reasoning billing must be mapped and tested, not guessed from an aggregate token count.
- Existing tutor/context/retrieval/grader boundaries remain responsible for evidence and source assembly. The deterministic kernel retains mastery, preferences and scheduling. Tool proposals and model judgments cannot publish curriculum or write learner state autonomously.
- Current routing inspection resolved chat to llama31-8b and simple explanations to gemma3-12b. Existing optional hosted baseline is openai-luna (gpt-6-luna). No assignments changed.
- Existing source-rights inventory identifies incomplete hosted eligibility enforcement: start hosted experiments with synthetic/publicly cleared fixtures only. Credentials and a budget are not permission to transmit private course material.

Relevant code paths are under `backend/app/`; reuse `scripts/eval_local_runtime.py`, `scripts/bench_model.py`, `backend/app/evals/` and existing result artifacts.

## Verified candidates and feasibility

Hardware inspected: Apple M4 Pro, 14 CPU cores, 48 GB unified memory; Ollama 0.33.3. Glimmer is not installed. Available local baselines include llama3.1:8b, gemma3:12b and gemma3:27b.

| Candidate | Verified availability | Feasibility / remaining compatibility work |
|---|---|---|
| Muse Glimmer 30B | Meta documents downloadable BF16/GGUF weights; Apache 2.0. Ollama publishes `muse-glimmer:30b` (18 GB) and `muse-glimmer:30b-mlx` (19 GB), text/image, 128K advertised context. | Quantized weights plausibly fit 48 GB, but context cache, OS, vision and concurrent models consume additional memory. Start at 8K context with one resident candidate; measure memory pressure. Installed runtime compatibility, digest and minimum version remain unverified. |
| Mistral Large 4 | Official API identifier `mistral-large-4`, public preview dated October 6; 1M context, structured outputs/function calling advertised. | 1.05T total / 52B active parameters: even ideal 4-bit weights imply about 525 GB before overhead. Not practical locally on this Mac. API only for this evaluation. |

[Meta artifact guide](https://dev.meta.ai/docs/muse-glimmer/get-the-model), [Ollama tags](https://ollama.com/library/muse-glimmer), [Mistral model card](https://docs.mistral.ai/models/mistral-large-4-0). Retrieved 2026-10-12. Sizes are published artifact sizes, not measured peak RAM.

Meta's prompting guide distinguishes reasoning and user output and describes native ATEM tool calls, one per turn. Validate final-answer extraction, token truncation and schema compliance through our adapter. Do not expose reasoning as the explanation or assume parallel tools. [Prompting guide](https://dev.meta.ai/docs/muse-glimmer/prompting).

Apple's MLX Swift repository contains a MuseGlimmer implementation; this does not establish compatibility with the installed Python MLX stack. Prefer the existing Ollama boundary, with its published MLX tag, over adding a Swift service. [Implementation](https://github.com/ml-explore/mlx-swift-lm/blob/main/Libraries/MLXVLM/Models/MuseGlimmer.swift).

Mistral's announcement says weights are due at the end of October. Do not treat announced weights as downloaded/released, or infer their final license. A pinned API revision, promotion expiry, cache eligibility and reasoning-token billing still need confirmation before paid execution. [Launch announcement](https://mistral.ai/news/mistral-large-4/).

## Comparison: measured versus untested

| Model | App evidence | Outcome |
|---|---|---|
| llama31-8b | Current chat assignment; no same-suite run included here | Retain default; obtain matched baseline in next experiment |
| gemma3-12b | Existing eight-case teaching suite, median total response 4.26 s | Material factual/attribution failures; not a quality pass |
| gemma3-27b | Same eight cases, median total response 10.78 s | Contradictory analogy and invented learner error; no routing promotion |
| Muse Glimmer | Official capabilities only; zero app calls | Untested |
| Mistral Large 4 | Official capabilities only; zero app calls | Untested |
| openai-luna | Existing adapter and historical evidence, no matched run here | Optional matched hosted baseline only after approval |

Reused `evals/results/teaching-12b-fixed-20261012.json` and `teaching-27b-fixed-20261012.json`; fixture hash `1f1827e6bedbada971f5f622c3115c0e3b5496e91e6af5d82ae67501fef2f718`. See `docs/LOCAL-EXPLANATION-DIAGNOSTIC.md` for case-level findings. Sixteen completed local calls belong to the prior experiment, not new work here. One run per case, mixed cold/warm conditions, mostly simple arithmetic: these medians are completion times, NOT time to first token, statistical rankings or learning-outcome evidence.

## Reproducible next experiment

First bounded slice: reuse the eight teaching cases against current chat, explanation baseline and Glimmer, with identical fixture hash, disposable SQLite database, hosted disabled and no fallback. Extend the existing harness's candidate allowlist only after download approval. Record model digest, runtime, context, reasoning setting, temperature, output cap, prompt version, warm/cold state and every attempt. Use a fixed seeded order and at least three repeats for latency; keep cold starts separate. Review answers blind to model identity.

| Dimension / use case | Required evidence beyond the existing smoke suite |
|---|---|
| Complex tutoring | Reference-checked ML, code and math explanations; correct examples, requested depth, one useful next step |
| Grounding | Exact source attribution, unsupported-claim count, adversarial source text; no invented citations |
| Misconceptions | Independently labeled answers including insufficient evidence; report agreement and false accusations; no cognitive diagnoses |
| Grading | Rubric agreement, valid alternative solutions and abstention cases; model judgment advisory |
| Curriculum review | Seeded omissions/ambiguous questions; trace proposals to sources; no publication writes |
| Bounded tools | Mock read-only retrieval/prerequisite tools; validate selection/arguments, maximum steps, failure recovery and forbidden-write rejection |
| Multimodal | Licensed synthetic charts/diagrams with ground truth; compare existing vision pipeline; do not silently coerce images into text messages |
| Latency/resources | Streaming first visible answer, total completion, p50/p95 over adequate samples, load time, peak memory and swap |
| Reliability | Malformed schema, empty/truncated answer, cancellation, timeout, retry/repair cost, no hidden fallback |
| Cost | Actual input/output/cache usage per attempt, reasoning billing if applicable, reservation reconciliation and unknown-billing handling |
| Learning value | Human review followed by learner comprehension/transfer checks; synthetic success alone cannot pass this gate |

Proposed promotion gate: zero critical factual/attribution failures on the reviewed fixed cases, no regression in valid-answer handling or learner control, and a demonstrated task-specific benefit at acceptable measured latency. Predeclare acceptance thresholds with the expanded fixtures; do not invent a single quality score after seeing results.

## Monthly Mistral cost estimate

USD, 30 days, one successful call per interaction, no caching, extra reasoning, repairs, retries or tool rounds in the base columns. Official rates per million tokens: regular input $1.36, cached input $0.14, output $4.18; sale $0.68/$0.07/$2.09. Sale expiry was not established. [Official pricing](https://docs.mistral.ai/inference/pricing), retrieved 2026-10-12.

| Scenario | Calls/day | Input/output per call | Regular/month | Sale/month | Regular with 50% input cache hits |
|---|---:|---:|---:|---:|---:|
| Light | 10 | 4,000/1,500 | $3.51 | $1.76 | $2.78 |
| Regular | 30 | 8,000/2,500 | $19.20 | $9.60 | $14.80 |
| Intensive | 80 | 15,000/5,000 | $99.12 | $49.56 | $77.16 |

Formula: `30 * calls_per_day * (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000`. Cache column assumes exactly half the input qualifies at the cached rate; it is an illustration, not a predicted hit rate. Sale cache costs would be half that column at the quoted rates.

A 10% rate of full repeated calls adds approximately 10% at equal token sizes. Multistep tools bill each model round, often with growing context. Extra billable reasoning/output tokens must be added at the provider-confirmed rate; verify whether reported output already includes them to avoid double counting. Taxes and any ancillary services are excluded.

Recommend an optional $10 initial evaluation ceiling, extendable explicitly to $20. Existing enforcement is DAILY, not a monthly cap: $1.50/day could permit $45 over 30 days. Before paid evaluation, reuse reservation/accounting plus an explicit cumulative campaign ceiling and provider-side limit where supported; test exhaustion, unknown usage and concurrent attempts. Do not describe a daily setting as monthly protection. Leave Mistral unregistered/disabled until this is implemented and approved; no credential was requested or exposed.

## Proposed routing — not applied

- Everyday chat, hints and simple explanations: retain current local assignments.
- Glimmer: opt-in local experiment for complex explanation/code review and evidence-grounded critique. Only promote a specific TaskClass after its gate passes.
- Mistral: opt-in comparison for tutor_deep, code_review or conflict_resolution; never automatic fallback during local-only evaluation. No need to change STT/TTS.
- Curriculum and misconception analysis: advisory structured proposals; deterministic validation and explicit human review before persistent changes.
- Tools/vision: separate later acceptance slices because the current generic message interface does not provide their native transport.

## Implementation, verification and next authorization

This slice adds this report only. No runtime, UI, assignments, credentials, dependencies, learner database or curriculum changes; no downloads or new model calls. Cost arithmetic was calculated with Python Decimal. Baseline artifacts and provider interfaces were inspected. Runtime tests/build/browser checks are not rerun for a documentation-only change; prior runtime results are cited rather than presented as fresh tests.

Next requested authorization should be specific: download the approximately 19 GB `muse-glimmer:30b-mlx` candidate and run bounded local synthetic evaluations. Resolve minimum runtime/digest first; use the ordinary 18 GB tag only as a separately documented alternative if MLX compatibility fails. Paid Mistral work requires separate approval for a dollar ceiling and adapter/accounting tests. No evidence currently justifies production integration.


## Authorized local installation and compatibility, 2026-10-12

Owner authorized19GB download; installed `muse-glimmer:30b-mlx`,19053621992 bytes,
digest `015fa21845bead56096c2f8773aff7a2047063507fe82897e662ad544c5b2fa6`.
Ollama show identifies safetensors/nvfp4,32.3B parameters,131072 declared context,
completion/vision/tools/thinking; no remote host/model metadata. This refines the
published30B product label, not an independently counted parameter total.

Local native chat smoke at8192 context, temperature0 and think:false:32 output-token
limit finished length with empty visible content (11.68s incl8.05s load);256 limit
answered5 correctly for2+3,39 generated tokens,1.90s warm total. This demonstrates
basic native transport only, not teaching, structured schema, vision, tools or reliable
reasoning suppression. Exact real app-path fixed-suite evaluation launched separately.
No live model assignment, learner database or paid provider changes.


## Completed app-path evaluation, 2026-10-12

The authorized fixed eight-case local trial is complete: five replies, three
`invalid_output` failures at the900-token limit. Median all-attempt response time
was39.704s; completed-only median33.134s. Baseline8b completed8/8 at3.555s median,
but also had factual/teaching failures. These single ordered runs do not prove a
stable speed ranking or overall teaching quality. See
[diagnostic review](../LOCAL-EXPLANATION-DIAGNOSTIC.md#glimmer-fixed-suite-result-2026-10-12)
and `evals/results/teaching-glimmer-fixed-20261012.json` for raw evidence.

Keep Glimmer installed as an experimental candidate, not a production assignment.
Correct arithmetic in completed replies does not offset missing responses and high
latency. No hosted calls, new paid integration, live curriculum edits or routing
changes were made. The original download-authorization paragraph above is historical;
the download and bounded trial are now completed.
