# Local semantic candidate search

Owner request: find useful previous replies before generating; reduce duplicate inference without treating generated text as truth.

## Boundaries and implementation order

1. Evaluate installed local embeddings using synthetic paraphrases and near-identical wrong answers. Record query/index latency separately; cosine similarity is relevance, never factual correctness.
2. Add a rebuildable private answer-vector cache keyed by learner, answer ID, answer fingerprint, embedding registry/model identity and embedding format version. Store separately from course corpus evidence. Cache updates happen after a successful answer save or explicit rebuild, not by embedding every historical answer during a question.
3. At request time embed only the bounded query. Filter ownership, target/workspace compatibility, visibility and reports before candidate selection; recheck original SQLite rows after retrieval so deleted/hidden/stale records cannot survive through a stale vector cache. Scope filters precede top-k, not after unrestricted ranking.
4. Fuse lexical and semantic candidates with explicit bounded top-k. Similarity may suggest earlier reasoning but must never enter exact-reuse eligibility. Exact replay still compares full request/history/workspace/prompt version and source checks.
5. On missing model, empty/corrupt cache, timeout or mismatched dimensions, fall back to local lexical retrieval. No download, hosted embedding or forced dependency setup during tutoring. Record retrieval latency/candidate IDs/route, not private text in logs.
6. Verify wipe/export/restore and embedding-model invalidation. No database migration until the chosen cache's backup/wipe lifecycle is implemented and tested. Avoid indexing all answers as corpus documents.

## Acceptance evidence required

- Paraphrase retrieval, hard negatives and task/owner isolation, including filtered top-k.
- Hidden/deleted/incorrect/outdated answers removed immediately despite stale index.
- Invalid dimensions/nonfinite vectors, model changes, missing model, concurrent rebuild and cancellation.
- Repeated warmed query timings and answer-generation comparison, not one cold batch.
- No increased confidence or mastery from match score; model-quality gates remain separate.

The initial diagnostic script uses unprefixed strings through the existing installed embedding adapter; this is an initial measurement, not a model-specific optimal configuration or completed integration.

## Initial measured result — 2026-10-01

`evals/results/answer-search/local-initial.json` records actual local nomic-embed-text output: six-document embedding batch 330 ms, four subsequent query embeddings 16/15/15/15 ms. These single trials exclude DB filtering/index lookup and generation, so they are not end-to-end latency guarantees.

Three of four top-ranked entries were the intended correct answers. The retention query instead ranked the intentionally incorrect inverted fraction first (0.7545), above the correct answer (0.7421). Both are strongly related semantically. This is useful negative evidence against any similarity-based correctness threshold or automatic replay of a paraphrase. Feedback/source/context gates must remain deterministic; an unreported wrong answer can still survive those gates, so generation quality must be evaluated independently.

No production embedding index, cache schema or semantic search endpoint has been installed by this diagnostic. Next bounded implementation is the owner-scoped derived cache and its deletion/model-version lifecycle, followed by request-time fusion with lexical retrieval.
