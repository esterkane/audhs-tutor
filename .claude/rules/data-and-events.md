---
paths:
  - "backend/app/db/**"
  - "backend/app/kernel/**"
  - "backend/alembic/**"
  - "docs/EVENT-SCHEMA.md"
---
# Data, kernel state & learning-event rules

- SQLite is the system of record. Qdrant (and any other index) is derived and rebuildable (`scripts/reindex.py`); `index_state` records the collection/embedding version.
- Tables: ARCHITECTURE §4. Schema changes go through Alembic (`/db-migration`). Every learner-scoped table has `learner_id`.
- `memory_state` is written only by the FSRS scheduler; `competency_evidence` only by the grader→kernel path; `competency_state` only by `kernel/competency.refresh(skill_id)` (idempotent, re-runnable). Never write mastery directly — it is computed.
- `learning_event` is append-only. Never UPDATE/DELETE rows (except the learner's whole-DB export/delete flow).
- Event envelope: `docs/EVENT-SCHEMA.md`. Verbs are a closed enum in `db/events.py`.
- Traces: every tutor turn writes `tutor_trace` (context sections + drops, action, prompt_version), `retrieval_trace` (query, bm25/vector/fused/reranked scores, chunk ids, flagged patterns) and `model_call` (provider, model, task, tokens, cost, latency, cached). A turn without a trace is a bug.
- `learner_preference` rows are structured (`key, value_json, origin ∈ explicit|proposed_accepted|inferred, confidence, reversible`), never free-text chat memory.
- `session_checkpoint` holds the last ContextPacket for resume; TTL 7 days; not an audit store.
- Preference pairs (`verb=preferred`) and delayed review outcomes (`verb=reviewed`) are the north-star signals for later personalization.
- Timestamps UTC ISO-8601; IDs ULID. `scripts/export.py` / `scripts/wipe.py` must keep working after every schema change — test it.
