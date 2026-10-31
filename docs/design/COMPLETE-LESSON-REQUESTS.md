# Complete bounded lesson questions

The lesson API accepts up to 4,000 characters, but the default ContextPacket request section
reserved only 400 approximate tokens. Requests above roughly 1,600 characters lost their tail
before inference, even though the full original request remained in saved history. A late
question or qualification could therefore be absent from the actual model input.

The default request reservation is now 1,000 approximate tokens, enough for the complete accepted
4,000-character request under the existing character-count budgeting function. Other section
reservations are unchanged. Provider context ceilings, output ceilings, exact optional tokenizer
counting and ordinary routing are unchanged. The API still rejects 4,001 characters. Explicit
smaller budgets used by internal callers remain bounded and report truncation normally.

For short questions the rendered messages and all other ContextPacket sections are byte-for-byte
unchanged. Longer valid questions are supplied in full; the existing provider sizing sees that
complete input. More input may require more processing, so this correction is not permission to
reduce output or history to recover latency.

Previously delivered answers remain historical snapshots. A retry with the same idempotency key
still replays the original saved result; a new turn uses the corrected context. No stored answer,
original request, checkpoint or curriculum material is rewritten, and no migration is needed.

Answers whose metadata explicitly records `request:truncated` are excluded from automatic
suggestions, lesson memory and embedding reuse by the shared owner-scoped eligibility policy.
Their original text, source records and even existing derived vectors remain stored. Direct
history access and idempotent replay remain available. Other budget-drop reasons and legacy
records without this flag retain their existing policy; exclusion is not a correctness verdict.

## Verification

Tests cover the length boundary, Unicode and inline code, full question delivery through buffered
and SSE endpoints, saved request/trace agreement, rejection above the API limit, unchanged short
messages and explicit smaller-budget truncation. The failure was reproduced before the correction.

One matched local-model comparison used a 3,900-character request with three questions at its end.
Captured provider arguments confirm that the old packet omitted all three questions while the
corrected packet contained the complete request. Both requests reserved 8,192 context tokens and
1,600 output tokens. The corrected answer covered all three requested points. Completion measured
11.569 seconds before and 8.248 seconds after, with first text at 9.556 and 5.465 seconds respectively.
This single pair is not a general speed ranking. The model still invented citation markers and a
source block; that separate grounding failure is unresolved and no model is qualified by this test.

The affected context consumers and the isolated upload-to-research-to-writing-to-review-to-lesson
workflow must pass before publication. This is a request-delivery correction, not a claim of broad
factual accuracy or a new model assignment.

Final local checks: 187 affected context, history, reuse, indexing, source and recovery tests pass;
strict mypy passes 330 source files and backend Ruff passes. The complete isolated browser workflow
passes in 18.8 seconds. These are scoped checks; newest-head GitHub CI remains independently required.
