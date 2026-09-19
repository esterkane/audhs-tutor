---
name: rag-ingest
description: Ingestion + hybrid retrieval conventions (Qdrant dense+sparse, provenance, trust tiers, poisoned-content guard, reindex). Use when adding a source type, changing chunking/embedding/ranking, or reindexing.
user-invocable: true
---
# Knowledge system (ADR-0002, ADR-0008)

Pipeline (`backend/app/knowledge/ingest/`): discover → extract → normalise → deduplicate (content hash per document version) → segment by lecture/section with timestamps → semantic chunk (300–500 tokens, lecture-level header prepended) → `chunk` + `chunk_provenance` in SQLite → dense embedding (`embed` TaskClass) + sparse (fastembed BM25/SPLADE) → Qdrant upsert with payload = provenance + `course/section/lecture/t_start/t_end/type/trust_tier/skill_ids`.

Provenance on every chunk: `source_id, document_id, chunk_id, path_or_url, content_hash, version, publication_date, ingested_at, source_type ∈ transcript|slide|code|notebook|doc|book|web, trust_tier ∈ owner_curated|course|official_docs|web_unverified`.

Retrieval (`knowledge/qdrant_hybrid.py` implements `RetrievalRepository`): Qdrant Query API prefetch dense top-N + sparse top-N → server-side RRF fusion with payload filters applied *inside* the search → optional local cross-encoder rerank → trust/provenance filter → `ScoredChunk[]` with all scores kept for `retrieval_trace`. k=8 default. Collections `corpus_v<embedding_version>`; scalar quantization + on-disk vectors on by default.

Guards: chunks are never inserted into the system role; `context.data_block()` wraps them with provenance headers and escapes; instruction-like patterns (`ignore previous`, `system:`, role tags) are flagged on the trace and left as quoted content. `tests/knowledge/test_poisoned.py` must pass.

Rules: idempotent by content hash; missing captions → local whisper transcription (`provenance.source_type=transcript, origin=whisper`); notebooks split by cell; slides one chunk per slide (+notes); switching embedding model → new `model_version`, `scripts/reindex.py` rebuilds all indexes from SQLite. Corpus is for personal study only — no export/share features for corpus content.

`SqliteHybridRepository` (FTS5 + sqlite-vec) implements the same interface for tests and offline fallback; never the production path.

CLI: `make ingest src=<dir>` → `scripts/ingest.py` (`--dry-run`, `--course`, `--force`, `--trust-tier`). Retrieval evals: `scripts/eval_retrieval.py` (recall@k on `evals/retrieval/*.yaml`).
