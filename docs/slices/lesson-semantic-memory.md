# Local semantic historical context for lessons

Extend literal lesson-history lookup with local cached embedding matches for paraphrases, while keeping the same skill, teaching contract and source-currency gates. Similarity supplies optional unverified historical context, never replay or learning evidence. A bounded lookup failure preserves normal generation. Existing history disclosure remains keyboard accessible; no sensory or teaching-mode changes. Indexing stays a separate local job; no model downloads or hosted embeddings.

Implementation and verification in progress. No quality or performance gate claimed.

## Implemented and verified

Lesson lookup now uses literal-first fusion with the shared local cosine ranker over at most 256 scoped cached answers. The same owner, skill, action, style and exact teaching-contract key filter applies before ranking. Current fingerprint/feedback and source hashes/newer versions are checked after embedding. No semantic match authorizes exact replay. A two-second optional lookup budget falls back to normal generation; rollback reloads request ORM state.

Contract-keyed lesson answers can be indexed using their original question text. Original answer bodies remain private derived input, never corpus truth. HTTP lesson completions schedule the same separate-session bounded indexing job as workspace replies. Voice turns can query the cache; websocket-only replies are indexed by a later indexing job or the explicit CLI, not by a new websocket background scheduler. Jobs are best effort, not durable; `scripts/index_answers.py` remains the recovery path. No provider downloads or paid embeddings occur.

Review found a freshness race in both tutor paths: lexical matches could survive a report/source change during semantic inference. Literal eligibility is now rerun after semantic success or failure before merging. Independent re-review found no remaining blockers/majors.

Verification: 473 backend tests and lint/types pass. New regressions cover paraphrase matching, teaching-contract mismatch, actual source edits during inference, negative feedback, buffered/SSE timeout recovery and post-response jobs, keyed lesson indexing and lexical-feedback rechecks. No frontend/schema change, so earlier UI/browser checks remain the evidence for unchanged disclosure controls.

A disposable local diagnostic (`scripts/eval_lesson_search.py`, raw result in `evals/results/answer-search/lesson-initial.json`) indexed one synthetic answer and found it for a paraphrase missed by literal search. One lookup took 50 ms, excluding answer generation; this is neither a general latency benchmark nor a quality gate. Broader end-to-end measurement, explicit/Socratic generation quality and opt-in exact lesson replay remain open. Earlier slice statement “in progress” describes its initial spec; this bounded implementation is now verified.
