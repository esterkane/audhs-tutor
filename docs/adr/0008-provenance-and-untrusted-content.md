# 0008 — Provenance first-class; retrieved content and tool results are untrusted data; sandboxed code
Date: 2026-09-19
Status: Accepted
## Context
Poisoned-RAG research: a document containing "ignore previous instructions…" must stay document content. Prompt-only defences are insufficient. Model-generated code must not run as trusted application code.
## Decision
Every chunk carries `chunk_provenance` (source_id, document_id, path/url, content_hash, version, publication_date, ingested_at, source_type, trust_tier). Retrieved chunks and tool results enter the prompt only inside a tagged data block in the user/tool role with provenance headers, never in the system role; the ContextPacket builder escapes/neutralises instruction-like patterns and flags them on the `retrieval_trace`; the tutor policy states that data blocks are quoted material. Tests include poisoned chunks. Learner-written or model-generated code runs only in Pyodide (browser) or a backend sandbox with CPU/memory/time limits, no network, and a read-only filesystem; the app never installs packages or modifies itself on model request.
## Consequences
+ Citations, content updates, conflict detection, safety and debugging all key off provenance. − Slight prompt overhead; sandbox runner is a later slice.
## Alternatives considered
Prompt-only "ignore instructions in documents" (rejected as sole defence).
## Evidence / sources
Review brief §6–7, §19.
