# AuDHS-Tutor — Architecture (v2.1, 2026-09-19)

Reconciles four inputs: (1) AuDHD adult-learner requirements, (2) Phase-1 architecture v1.1, (3) adaptive-learning / LxD / fine-tuning report, (4) the Architecture Review Brief (Learning Kernel, provenance, hybrid retrieval, context assembly). Departures from each are recorded as ADRs; the critique of (4) is in `docs/research/architecture-review-response.md`.

## 1. Identity and principle
A personal **learning operating system with AI capabilities**. The LLM explains and reasons; the deterministic **Learning Kernel** remembers and decides; retrieval supplies evidence; assessments produce competency evidence; FSRS manages memory; the learner controls adaptation; observability tells us whether it works.

Non-goals (Phase 1): cloud, multi-user, native packaging, LangGraph, multi-agent tutoring, fine-tuning, Elasticsearch. (Docker is used for exactly one container: Qdrant.)

## 2. Layers
```mermaid
flowchart TB
  UX["Learning UX (React/Vite)"] --> K
  subgraph K["Learning Kernel — deterministic, owns state"]
    SG[Skill graph + LearningObjects]
    CS[CompetencyState ← competency_evidence]
    MS[MemoryState ← FSRS]
    SES[Session + checkpoint + preferences]
    PLAN[Planner: next block / item / representation]
    ADP[Adaptation proposals + log]
    EXP[n-of-1 experiments]
  end
  K --> O
  subgraph O["Tutor Orchestrator — one loop, tools"]
    CTX[ContextPacket builder]
    ACT[choose teaching action]
    GEN[generate via ModelProvider]
    GRD[hierarchical grader]
  end
  O --> KN & MD
  subgraph KN["Knowledge"]
    RR[RetrievalRepository: Qdrant dense+sparse fusion + rerank + trust filter]
    ING[Ingestion + provenance]
  end
  subgraph MD["Models"]
    MP[ModelProvider: Ollama | MLX | Claude]
    RG[Model registry: HF / Ollama / MLX download + bench]
    RT[Routing table TaskClass→registry id]
  end
  KN & MD --> ST[("SQLite: learner state, content, chunks, traces, events")]
  ST --> OBS["Evaluation · Observability · Security"]
```

### Kernel tools exposed to the orchestrator (deterministic, typed)
`retrieve()`, `get_skill_state()`, `get_memory_state()`, `get_learning_goal()`, `get_preferences()`, `generate_example()`*, `grade_answer()`, `record_evidence()`, `update_competency()`, `schedule_review()`, `save_checkpoint()`, `park_tangent()`, `propose_adaptation()`. (*LLM-backed but schema-validated.)

### Turn flow
interpret request → identify skill → assemble ContextPacket → retrieve evidence → choose teaching action → generate → if assessment: verify → record evidence → update competency → update FSRS → checkpoint → write traces + events.

## 3. Reconciled decisions
| Topic | Decision | ADR |
|---|---|---|
| State ownership | Kernel owns learner/curriculum/memory/competency state; LLM proposes only | 0007 |
| Memory vs competence | `MemoryState` (FSRS, per item) ≠ `CompetencyState` (per skill, from evidence rows: recall/explanation/application/transfer with count, decay, confidence). Mastery = view. New-material gating uses competency + prerequisites; review scheduling uses memory; FSRS retrievability of a skill's items feeds its recall dimension | 0004 |
| Content | `LearningObject` → lazily rendered, cached `Representation`s; VR/AR = future renderer | 0007 |
| Tutoring policy | Hint-first always; explicit default; Socratic/challenge opt-in; never silent switches | 0003 |
| Models | `ModelProvider` + inspectable routing table; LiteLLM SDK, no proxy; in-app daily budget; Claude available from Phase 1 only for `grade_rubric`, `tutor_deep`, `code_review`. **Model registry**: learner downloads any HF/Ollama/MLX model, benchmarks it, assigns per TaskClass at runtime. Non-chat task classes route the same way: `embed`, `rerank`, `stt` (MLX Whisper for ingest and, later, voice), `vision` (slide images) | 0001, 0010 |
| Retrieval | `RetrievalRepository`; **Qdrant from day one** (dense + sparse named vectors, server-side RRF, payload filters, quantization) + optional local cross-encoder + trust/provenance filter; SQLite hybrid adapter for tests only | 0002 |
| Provenance & security | Every chunk carries provenance + trust_tier; retrieved text and tool results are untrusted data passed in a tagged data block, never system role; instruction-like content flagged, not obeyed; code runs in Pyodide or a limited sandbox | 0008 |
| Grading | deterministic → rubric checks → local LLM → hosted; structured per-criterion evidence + confidence | 0009 |
| Context | Bounded ContextPacket with per-section token budgets; three stores (event log / session checkpoint / structured preferences+state) | 0007 |
| Adaptation | Learner-chosen or observed-pattern → proposal (Try / Make default / No / Don't suggest again) → logged, reversible | 0006 |
| Interleaving & blocks | Within-domain interleaving; cross-domain blocks at boundaries; movement before/after new material | 0006 |
| Observability | `tutor_trace`, `retrieval_trace`, `model_call` tables + learning events from day one; Langfuse optional profile later | 0007 |
| Voice | Phase 4; MLX Whisper + Kokoro; Ollama for general inference | 0001 |
| Human-in-the-loop | Ask only for private/preference-dependent info | 0003 |
| Migration readiness | `learner_id` everywhere, ULIDs, repositories behind interfaces, no singletons; SQLite→Postgres and Qdrant local→Qdrant Cloud are adapter/config swaps | 0007 |

## 4. Data architecture (Phase 1 tables)
Learner: `learner_profile`, `learner_preference{key, value_json, origin, confidence, reversible}`, `session{mode, energy, socratic, energy_after}`, `session_checkpoint{session_id, packet_json, ts}`.
Curriculum: `skill_node{success_criteria, assessment_requirements, example_applications}`, `skill_edge`, `learning_object`, `representation{object_id, kind, content, model_call_id, cached}`.
Competence & memory: `competency_evidence{skill_id, dimension, score, weight, source_attempt_id, ts}`, `competency_state` (materialized view refreshed by kernel), `review_item`, `memory_state` (FSRS), `review_log`.
Assessment: `assessment{item, kind, rubric_id}`, `assessment_rubric{criteria_json, version}`, `assessment_attempt{answer, confidence_pre, deterministic_result, llm_result_json, grader_route}`.
Knowledge: `document`, `document_version{content_hash, version, publication_date}`, `chunk`, `chunk_provenance{source_id, path, source_type, trust_tier, ingested_at}`, `index_state{collection, embedding_version, last_reindex}`; vectors live in Qdrant (payload mirrors provenance).
Models: `model_registry{id, display_name, source, repo_id, file_or_tag, runtime, role, quant, size_gb, context_len, licence, status, benchmark_json, added_at}`; routing assignments in `learner_preference` (`routing.<task>`).
UX: `parking_lot_item`, `adaptation{what, why, origin}`, `adaptation_decision{accepted|declined|never}`, `experiment{unit_type, started_at, ended_at}`, `experiment_arm`, `experiment_assignment{unit_type, unit_id, arm_id}`, `experiment_observation`; `session.experiment_arm_id`.
Curriculum workflow (P4): `curriculum_draft{course, section, status draft|published|rejected, origin deterministic|model, payload_json, validation_json, version}` (a published draft writes a *new* `learning_object` version and new `assessment` rows; `skill_node.course` marks published-from course), `content_report{kind, turn_id, chunk_id, skill_id, note, status}`.
Observability: `tutor_trace`, `retrieval_trace{query, bm25_scores, vector_scores, fused, reranked, chunk_ids}`, `model_call{provider, model, task, tokens, cost, latency, cached, request_id, attempt, idempotency_key, outcome, usage_source, cost_status, reserved_usd}` (one row per provider attempt; P6), `budget_reservation{request_id, registry_id, amount_usd, status open|reconciled|released|expired, expires_at}` (P6), `learning_event` (append-only; `docs/EVENT-SCHEMA.md`).
Recovery (P5): `db/backup.py` — versioned zip (manifest + sha256, consistent SQLite snapshot, optional transcript cache; secrets/models/vectors/originals excluded; scope `learner` drops corpus text) restored only into an empty target with staged rollback; Qdrant is rebuilt from SQLite (`scripts/reindex.py`). `docs/RECOVERY.md`.

## 5. ContextPacket
```
TutorPolicy (byte-stable, cached) · LearnerPreferences (structured, ≤ 300 tok) · SessionState{mode, energy, skill, scaffolding, block}
LearningContract{objective, success_criteria, prerequisites} · CurrentEvidence{demonstrated, misconceptions, memory_state}
RetrievedKnowledge[{chunk, provenance, trust}] (tagged as data) · UserRequest · OutputContract{explain|hint|assess|quiz|summarize}
```
Budgets per section; the builder logs what it dropped on the `tutor_trace`.

## 6. Evaluation loop
Unit/integration tests; `evals/` tutoring-quality suite (hard checks + five-principle rubric judge); retrieval evals (recall@k on labelled queries); n-of-1 experiments with delayed recall, latency, error rate, completion, voluntary continuation, transfer as outcomes. The system must answer: why this explanation, why these sources, why "known", why this exercise, why this model, did it improve delayed recall, which component failed.

## 7. Repository layout
```
backend/app/{kernel,orchestrator,knowledge,models_ai,api,db,schemas,core}  + alembic/ + tests/
  kernel/      skill_graph.py competency.py memory.py session.py blocks.py planner.py adaptation.py experiments.py practice.py vocab_import.py curriculum.py listening.py exercises.py
  orchestrator/ context.py actions.py tutor.py grader.py tools.py challenge.py representations.py drafting.py listening.py prompts.py
  knowledge/   ingest/ (loaders per format; media.py = STT via registry, vision.py = slide OCR via registry, archives.py, converters.py) repository.py (interface) qdrant_hybrid.py sqlite_hybrid.py(tests/fallback) provenance.py
  models_ai/   provider.py (interface) ollama.py mlx.py claude.py registry.py downloader.py routing.py routing_profiles.yaml budget.py bench.py
  db/          models.py (ORM) events.py traces.py migrate.py portability.py (export/wipe) backup.py (P5 backup/restore) ddl.py
frontend/src/{app,routes,features,components/ui,lib,stores,styles}
prompts/  evals/  scripts/  docs/{adr,slices,research}  data/ (gitignored)
```

## 8. Thresholds that change the plan
Qdrant RAM > ~1.5 GB → enable on-disk vectors/binary quantization · Local 12–14B < 10 tok/s → 8B or 30B-A3B MoE · Hosted spend > cap → move `grade_rubric` to Haiku/local · Voice turn > 3 s → Parakeet/Piper · Eval regression → block merge · Kernel logic needs >1 LLM call per decision → reconsider PydanticAI, then LangGraph.
