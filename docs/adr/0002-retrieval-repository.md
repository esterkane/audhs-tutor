# 0002 — RetrievalRepository interface; Qdrant hybrid from day one
Date: 2026-09-19
Status: Accepted
## Context
Corpus will grow to 50–200 Udemy courses (25k–125k+ chunks). Exact-term matching (LoRA, ReLU, torch.nn.Module, error strings) matters as much as semantics; retrieval must filter by course/section/lecture/skill node inside the index. The owner chose Qdrant and wants it from day one; the review brief's FTS5 + sqlite-vec option is kept only as a test/fallback adapter.
## Decision
`RetrievalRepository` interface (`search(query, filters, k) → [ScoredChunk with provenance]`, `upsert`, `reindex`) is binding. Production implementation from Stage 0: **Qdrant** (single Docker container) with named vectors — dense (`embed` TaskClass) + sparse (fastembed BM25/SPLADE) — fused server-side (RRF/DBSF via Query API), payload = full provenance + `course/section/lecture/t_start/t_end/type/trust_tier/skill_ids`, scalar quantization + on-disk vectors to keep RAM under ~1 GB. Optional local cross-encoder rerank and trust filter happen in the repository after fusion. Raw chunks + provenance always live in SQLite; `scripts/reindex.py` rebuilds Qdrant from SQLite. Collection name `corpus_v<embedding_version>`; embedding model changes = new collection. A `SqliteHybridRepository` (FTS5 + sqlite-vec) exists for tests and as an offline fallback only.
## Consequences
+ HNSW at scale, hybrid + filtered search, cloud-portable, matches owner's stated preference and ES intuition. − One container required in Phase 1 (Docker/OrbStack); two stores kept consistent by reindex.
## Alternatives considered
FTS5 + sqlite-vec as default (rejected by owner; kept as fallback adapter), Elasticsearch (JVM memory competes with local LLM), LanceDB.
## Evidence / sources
docs/research/phase1-architecture-v1.1.md §4a; review brief §5–6; owner decision 2026-09-19.
