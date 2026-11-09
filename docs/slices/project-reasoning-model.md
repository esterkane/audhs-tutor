# Explicit reasoning model for project explanations

The Supabase/PostgreSQL project setup offers a reasoning tutor alongside the existing local and OpenAI Luna choices. The reasoning choice selects registered GPT-6.1 Sol with medium reasoning through the Responses API. The current model is displayed, and the controls explain its higher cost and potentially longer wait. Existing stored preferences are not migrated automatically; omitted model choices retain Luna for API compatibility.

Provider and model are saved atomically after checking the existing shared authoring budget and credential configuration. Selecting a model does not perform inference or modify a learning session. Local accepted-material reuse, embeddings and other task assignments are unchanged. Study authorization remains bound to exact requests, and model attempts use the existing shared ledger and cap.

The Responses adapter keeps every supplied message, disables provider-side storage and SDK retries, and preserves original schema validation. Only disjoint tagged unions are translated to the wire format; open objects are encoded and restored using their schema. Unsupported ambiguous unions fail before sending. Incomplete/refused outputs are rejected while reported usage, including reasoning tokens, is retained. It does not silently switch to Chat Completions for streaming. Actual transport and effort are recorded in attempt metadata.

Official model/pricing documentation verified 2026-11-02: https://developers.openai.com/api/docs/models/gpt-6.1-sol and https://developers.openai.com/api/docs/pricing . Registry context is 1,050,000 tokens. Conservative standard-service long-context/cache-write ceilings of $10/M input and $15/M output protect the shared budget; these are not an invoice estimate for typical short requests. Existing normal daily limits remain unchanged.

Qualification is bounded: manually reviewed English write-skew, grants/RLS, concurrent conflict visibility and caller-privilege ambiguity cases, plus German transaction and vector explanations. Medium reasoning resolved the observed caller-privilege omission in the tested runs, but does not guarantee general factual accuracy. Fresh answers can still take tens of seconds. Source-based local reuse remains preferable when it meets the request.

Validation: 447 scoped backend tests passed; Ruff, mypy, frontend TypeScript build and changed-file ESLint passed. An isolated browser workflow selected the reasoning model through the actual setup button, verified failed setup preserves local routing, completed two German explanations, reloaded the full transcript, and exercised budget refusal (50.0 seconds test, 58.9 seconds including startup). Manual review confirmed the requested transaction and vector conclusions. A citation-only repair took 2.359 seconds. These measurements do not establish a general speed improvement.


## Avoid duplicate tool structure

The Responses route now leaves tool input structure to its enforced response schema and retains every human-readable tool annotation in the prompt. Other hosted transports keep their existing full tool catalogue. Full prior messages, request policy, output allowance, source requirements and model effort are unchanged.

Regression tests cover both hosted paths, all retained annotation types and exact prior-message preservation. 448 scoped tests passed; Ruff and mypy passed. The isolated full browser workflow passed in 47.5 seconds (57.4 including startup), and manual review confirmed the complete transaction/vector answers. The first identical learner request used 12,046 input tokens instead of 12,595, a reduction of 549. Total time versus the previous 50.0-second test is not a controlled decoding benchmark; extra retrieval and repair choices varied. The supported result is reduced duplicated input with preserved tested behavior, not guaranteed latency improvement.

## Lossless long-session wire formatting

Structured historical message blocks now use compact JSON separators on the bridge-to-model boundary. This removes only formatting outside JSON string values. Message order, roles, every field and value, whitespace inside SQL/prose, source identifiers and saved transcripts remain unchanged. String messages are sent verbatim. There is no generated summary, truncation, source deduplication or history deletion.

An offline replay through the actual bridge with a fake gateway measured synthetic histories at 1, 10, 30, 60 and 120 turns. Using o200k_base estimates (not billed provider usage), baseline input was 1,882 / 10,306 / 29,026 / 57,106 / 113,266 tokens. Compact formatting used 1,865 / 10,136 / 28,516 / 56,086 / 111,226: savings reach 2,040 tokens (1.8%) at 120 turns. The fixture includes three documentation excerpts per turn and preserved prior answers. It is a workload example, not a prediction of every learner session; counts exclude the separate response schema. Growth remains linear because source text and answers remain complete.

Lossy summarization and source-reference replacement are deferred: the current guard consumes the original source-bearing transcript, and historical source identity/availability must remain reliable. This small reduction does not solve long-session growth or establish faster decoding.

Validation: 51 bridge/Responses adapter tests, Ruff and targeted mypy passed. A 120-message regression checks round-trip equality, exact SQL/prose whitespace, message roles/order and unchanged input history.

The real isolated Chromium workflow passed (45.8 seconds test, 57.0 total): model selection/setup failure, two source-backed explanations, no forced quiz, transcript reload and budget refusal. Manual review confirmed concurrent absolute versus relative balance updates and all requested NOT IN/NOT EXISTS NULL cases. Generation calls were 13.366 and 12.519 seconds; this is not a controlled speed comparison. No saved transcript was compressed or discarded.

## Canonical tool-result JSON formatting

Tool results contain serialized JSON inside historical message JSON. The wire adapter now removes redundant formatting in that inner layer too, but only when the original body exactly matches canonical JSON emitted by the tool adapter. Duplicate keys, custom numeric spellings, nonfinite numbers, malformed JSON and plain text are left alone. Source/SQL string values, fields, order, tool identities and persisted messages are retained. It does not deduplicate evidence or replace it with references.

The same synthetic history measured an additional 17 / 170 / 510 / 1,020 / 2,040 estimated tokens saved at 1 / 10 / 30 / 60 / 120 turns. At 120 turns the previous release used 111,226 estimated tokens and this candidate 109,186 (1.83% less; 3.60% below the original 113,266). These are o200k_base estimates excluding response schema, not provider billing or a decoding speed benchmark. Full histories still grow linearly.

Validation: 61 wire/bridge/Responses tests passed; targeted mypy and Ruff passed. Coverage includes exact source and SQL whitespace, large integers, nulls, unchanged input history, preserved tool identity, malformed/duplicate-key/noncanonical bodies and unchanged learner/assistant text.

The isolated real-provider Chromium workflow passed (39.9 seconds test, 48.9 total), including model setup/failure, source-backed explanations, full transcript reload and budget refusal. Manually reviewed balance-update and NULL answers remained correct. The two explanation calls took 8.988 and 13.604 seconds; uncontrolled timing differences do not establish a general speedup.

## Verified search provenance and bounded parsing

The inner JSON transformation now requires one uniquely identified preceding assistant search_docs call and one successful user result with that ID. Reused or colliding IDs anywhere in the request, other tools/roles, missing success markers and unrecognized envelopes leave the body unchanged. The search envelope must include the expected result fields. Bodies over 256×1024 characters are skipped before JSON parsing. This is a request-format check, not cryptographic provenance or factual verification.

The full original request still supplies guard/citation checks and persisted history. Only the copied model-facing representation changes. A mixed 120-message regression exercises 20 eligible inner compactions, unrelated tools and errors, exact source/SQL whitespace, message order and original-history equality. Unit tests also cover unusual numbers, malformed/noncanonical bodies, future ID reuse and oversized parser bypass.

96 wire/bridge/Responses/factual-manifest tests passed; full application/test Ruff lint and formatting passed; targeted mypy passed. The accompanying factual manifest supplies eight EN/DE review cases and distinguishes existing oracle capabilities from planned observations; it does not certify a model or replace manual semantic review.

An independent offline synthetic reference experiment shows why larger compression is deferred: whole-result references save heavily for exact repeats but nothing when scores or timestamps change. Passage references require explicit identity/version and per-occurrence metadata. Neither exact reconstruction nor synthetic token savings proves model comprehension. No reference-based compression is activated.

Integrated real-provider Chromium workflow passed (44.1 seconds test, 54.0 total), covering setup/failure, complete source-backed answers, transcript reload and budget refusal. Manual review confirmed the absolute-versus-relative update and NOT IN/NOT EXISTS NULL cases. Explanation calls took10.379 and12.249 seconds, without a general latency claim. Independent read-only code review found no actionable defect in the final provenance/size/history safeguards.
