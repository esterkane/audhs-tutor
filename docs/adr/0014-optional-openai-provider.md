# 0014 — Optional OpenAI provider within local-first routing
Date: 2026-09-24
Status: Proposed

## Context
The owner requested the cheaper hosted option, approved implementation, supplied a local key and
clarified that tasks should execute locally whenever accurate and capable. Existing hosted runtime
entries are Anthropic-specific. Availability and low price do not prove tutoring accuracy.

## Decision
Extend the existing ModelProvider/gateway boundary with a separate OpenAI provider/key/runtime.
Use GPT-6 Luna as the evaluated budget candidate. Keep current assignments; hosted execution is
for demonstrated task-specific gaps. Do not equate key configuration or a transport benchmark with
a pedagogical quality gate. Preserve Claude as an optional independently configured provider.

All hosted providers and benchmarks share reservation/accounting rules. Include structured schemas
in reservations; preserve unknown billed cost when an interrupted stream lacks final usage. Keep
secrets server-side, send no learner/course content in compatibility tests, and use disposable DBs.

## Consequences (positive / negative / follow-ups)
Cheaper hosted capability is available without replacing local inference. This adapter uses verified
Chat Completions/tool compatibility with reasoning disabled; arbitrary model compatibility is not
claimed. Conservative estimates can overstate billing and block requests earlier. Independent CLI
processes still have separate budget locks. Broad tutor/grader evaluation and selective escalation
remain follow-ups, not completed gates.

## Alternatives considered
A blanket hosted switch would ignore the owner's local-first requirement. Reusing Anthropic's
runtime would confuse keys/readiness and accounting. Staying entirely local leaves the demonstrated
whitespace-debugging error unresolved for tasks needing a more accurate fallback.

## Evidence / sources
Owner's implementation approval and local-first clarification, 2026-09-24.
`docs/PROVIDER-COST-COMPARISON.md`, `docs/slices/openai-provider.md`,
`evals/results/report-2026-09-24-openai.md`.
[Official model/API support](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[pricing](https://developers.openai.com/api/docs/pricing).
