# Hosted provider cost decision — 2026-09-24

Selected budget candidate: **OpenAI GPT-6 Luna** only when a local model cannot perform a task accurately, subject to task-quality evaluation. Local execution is the default (owner clarification, 2026-09-24). Do not infer equivalent teaching quality from a lower token price.

Standard short-context list rates, USD per million tokens, checked on official pages:

| Model | Input | Output | Example: 1,000 turns |
| --- | ---: | ---: | ---: |
| GPT-6 Luna | $0.10 | $0.50 | $0.45 |
| Claude Haiku 4.5 | $1.00 | $5.00 | $4.50 |
| GPT-6 Sol | $2.00 | $10.00 | $9.00 |
| Claude Sonnet 5 | $2.00 | $10.00 | $9.00 |

Example assumes exactly 2,000 uncached input and 500 billed output tokens per turn. It excludes tool charges, taxes, retries, regional uplifts and extra reasoning tokens. Tokenization, answer length and quality can differ. Sonnet's older $3/$15 rate was superseded by its permanent $2/$10 price; do not use the stale rate.

Sources: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [Claude Haiku](https://www.anthropic.com/claude/haiku), [Sonnet 5 pricing update](https://www.anthropic.com/news/claude-sonnet-5).

## Integration status

OpenAI is integrated as a distinct provider/runtime. OPENAI_API_KEY is server-side configuration;
Claude remains available through its own key and entries. Existing routing defaults and learner
assignments are unchanged. Presence of a key means configured, not verified quality or account access.

A capped synthetic evaluation completed six requests: four playground cases, one typed response
and one stream. Estimated total: $0.000725. Luna correctly explained the whitespace bug missed by
the local model. Hint granularity and broader grading quality remain unevaluated or incomplete;
this does not justify a blanket switch. See `evals/results/report-2026-09-24-openai.md`.

App estimates deliberately price all input at the short-context cache-write ceiling ($0.125/M),
with output $0.50/M, ignoring cache-read discounts. They are conservative estimates, not invoices.
The adapter bounds prompt size below the long-context tier, uses standard processing, disables
reasoning for Chat Completions/tool compatibility and disables hidden transport retries.
Reservations include structured schemas and wrapper allowance. Interrupted streams lacking final
usage retain unknown billing at the reserved amount. Paid model benchmarks use the same accounting.

The API key is excluded from Git, browser storage, backup reconstruction and docs. No course content
or learner records were sent in this synthetic evaluation. Provider pricing/account limits can change;
keep the local daily cap and provider-side billing limits configured.
