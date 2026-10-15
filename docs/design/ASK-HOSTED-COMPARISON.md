# Bounded Ask hosted comparison

Status: prepared 2026-10-15; owner authorized preparation, not execution or spending. No production routing change. This is separate from the completed earlier hosted trial and must never reuse or reset that trial's journal.

## Question and frozen cases

Does one pinned hosted model avoid the concrete unsourced explanation and source-review errors observed locally? Use five original synthetic cases, one attempt each:

1. Explain why fitting an imputation median on training and held-out inputs leaks information, direct mode.
2. The same question in explicitly guided mode.
3. Review the recorded incorrect synthetic answer against a training-only reference: identify the contradiction.
4. Review a correct training-only claim against the same reference: support it with exact quotes.
5. Review that claim against an unrelated audio reference: report insufficient evidence.

The frozen synthetic campaign (`evals/cases/ask-hosted-campaign.json`) contains exact messages, hashes, rubric and baseline references. It excludes course passages, real learner conversations, personal profile text, credentials and local paths from outgoing messages. Synthetic passage IDs are disposable fixture identifiers. Do not load the live database or interpolate runtime user context. The two longer grounded-generation packets are deliberately excluded because their system text includes personal background.

The three checker cases replay the previously tested separated answer/source candidate, not the unchanged production checker. Schema serialization/transport differs across providers. Preserve these distinctions in the report; do not present results as a controlled hardware comparison or validation of production integration.

## Proposed cost and transport bounds

Candidate: OpenRouter `meta/muse-glimmer-30b`, pinned `deepinfra/bf16`, no fallback, no retries or repairs. Request at most 2048 output tokens, temperature 0.2. Review cases require the existing AnswerReviewProposal schema; generation returns text. Never count private reasoning as the learner-facing explanation.

Official endpoint catalog read on 2026-10-15 reports input $0.30/M, output $1.20/M, context 131072, maximum completion 16384, and structured output support. Recheck the exact contract before sending. Reject price/limit/provider changes or nonzero per-request fees.

Reserve conservatively for the entire advertised input window plus the entire advertised output maximum, even though requests are smaller, with the existing 5.5% allowance:

`(131072 × 0.0000003 + 16384 × 0.0000012) × 1.055 = $0.062226432 per attempt`

Five attempts reserve **$0.31113216**. Request an explicit **$0.32 total ceiling**. This is a maximum authorization, not an exact bill or a promise about taxes/account fees. No cache discount is assumed. The earlier trial's unused approval is not reused.

Before execution, the dedicated runner must pass offline tests for frozen-input hash enforcement, a five-attempt persistent journal, reserve-before-send, restart without resend, concurrent invocation, unknown billing halt and price drift. Reuse established transport/accounting behavior without changing the earlier campaign's constants or journal. No execution until both these gates and explicit owner cost approval are satisfied.

Freeze the complete request body, including the review JSON schema, provider pin, output limit and temperature. Do not load a newer application schema at execution time. Bind approval and the durable journal to the whole campaign hash and retry policy; consume each attempt before network delivery. An uncertain delivery cannot release its reservation or be resent. Send only the frozen request body, never baseline paths or report metadata. The sidecar hash is for review; the runner must embed the approved digest rather than trust an independently editable sidecar.

Validate returned model/provider, usage, cost and finish reason. For generation, measure first visible answer text; for review JSON, label timing as first JSON content rather than learner-facing explanation latency. Invalid schema, missing targeted-claim coverage, empty or truncated output is a failed case even if billing is known. Apply exact quotation binding without creating a local-model review receipt.

## Interpretation and stopping rule

Use deterministic arithmetic and exact-quotation validation plus independent semantic review. A critical false teaching claim, incorrect support verdict, empty response or truncation fails that case. Report missing claims and check coverage; no whole-answer verified label. Do not persist hosted output as a local-model review receipt.

Record provider/model, actual reported usage/cost, prompt hashes, output cap, time to first visible text and total response time. Keep failed/empty outputs in the denominator. Five single samples cannot establish general accuracy, reliable latency percentiles, or improved learning. The higher output cap differs from some local records; report that confound rather than declaring a performance winner.

Stop after five attempted calls, or immediately on uncertain accounting/transport outcome. No automatic retesting, provider switch, production adoption, grading or scheduling change. A favorable result supports a separate integration decision only.

Official references:
- https://openrouter.ai/meta/muse-glimmer-30b
- https://openrouter.ai/api/v1/models/meta/muse-glimmer-30b/endpoints
- https://openrouter.ai/docs/guides/routing/provider-selection

## Prepared runner verification

`scripts/eval_ask_hosted.py` defaults to an offline preflight. Full frozen campaign SHA-256: `24bd2a619d741c1a176c45706b86046d9f22e4c207bdf4f986a9c8734be3491d`. Execution requires that digest as an explicit argument after owner spending approval; knowledge of the digest is not authorization. The journal is separate from the earlier completed campaign.

39 offline tests pass across the new campaign and reused transport/preflight suites, including complete mocked execution twice with only five requests, pending restart, concurrent reservations, unknown/excess charges, changed input/schema, and invalid quote retention. Ruff and strict script mypy pass. Independent code review found no blockers or majors. No UI changed, so no browser or accessibility pass is claimed. No real model calls ran; semantic review and target-claim coverage remain pending.
