# Hosted provider cost decision — 2026-09-24

Selected budget candidate: **OpenAI GPT-6 Luna** for routine tutoring, subject to task-quality evaluation. Keep local models available. Do not infer equivalent teaching quality from a lower token price.

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

Selection only: OpenAI is not yet wired into the app and live routing has not changed. Existing hosted runtime assumes Anthropic. Before enabling OpenAI, add a distinct provider/configuration, provider-aware registry/readiness, streaming/structured output support and the shared hosted budget/accounting path. Test billing and fallback behavior; evaluate hints, explanations and grading separately. Never classify OpenAI usage as free local inference.

The API key belongs in local environment configuration, never chat, frontend storage or Git. No key was requested or accessed for this comparison; no paid requests were made. Preserve Claude as an optional provider rather than overwriting its registry entries.
