# 0008 — Provenance first-class; retrieved content and tool results are untrusted data; sandboxed code
Date: 2026-09-19
Status: Accepted
## Context
Poisoned-RAG research: a document containing "ignore previous instructions…" must stay document content. Prompt-only defences are insufficient. Model-generated code must not run as trusted application code.
## Decision
Every chunk carries `chunk_provenance` (source_id, document_id, path/url, content_hash, version, publication_date, ingested_at, source_type, trust_tier). Retrieved chunks and tool results enter the prompt only inside a tagged data block in the user/tool role with provenance headers, never in the system role; the ContextPacket builder escapes/neutralises instruction-like patterns and flags them on the `retrieval_trace`; the tutor policy states that data blocks are quoted material. Tests include poisoned chunks. Learner-written or model-generated code runs only in Pyodide (browser) or a backend sandbox with CPU/memory/time limits, no network, and a read-only filesystem; the app never installs packages or modifies itself on model request.
## Amendment 2026-09-19 (Stage 3, untrusted-content-guard)
Flagged chunks with `trust_tier < 2` (untrusted, web) are dropped before the ContextPacket is built and logged as `retrieved:<id>:quarantined` in `tutor_trace.dropped`; the Session screen tells the learner how many sources were withheld. Flagged chunks from tier ≥ 2 (purchased course, owner-verified) are kept, escaped and headed with `flags=` — a course that teaches prompt injection must remain citable. The threshold is `QUARANTINE_BELOW_TRUST` in `orchestrator/context.py`. The owner can re-tier a document from the Corpus screen (`PATCH /api/corpus/documents/{id}`) instead of re-ingesting. Pattern scanning runs on NFKC-normalised text with invisible characters stripped.
## Consequences
+ Citations, content updates, conflict detection, safety and debugging all key off provenance. − Slight prompt overhead; sandbox runner is a later slice.
## Alternatives considered
Prompt-only "ignore instructions in documents" (rejected as sole defence).
## Evidence / sources
Review brief §6–7, §19.
