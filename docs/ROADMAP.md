# Roadmap

**Current stage:** 0 — Skeleton (in progress — `repo-bootstrap` done 2026-09-19)

Order follows the Architecture Review Brief: prove the learning loop first, then the kernel, then the knowledge system, then adaptive UX, then frontier+voice, then offline agents. Each stage: slices (`/feature-slice`), a benchmark script, exit criteria.

## Stage 0 — Skeleton (½ day)
- [x] `repo-bootstrap` — `scripts/bootstrap.sh`, Makefile, `.env.example`, uv + pnpm projects, ruff/prettier, Qdrant container (`make services`).
- [x] `db-core` — ORM + Alembic for all Phase-1 tables (ARCHITECTURE §4); `learning_event` append-only; `learner_id` everywhere; export/wipe scripts + test.
- [x] `model-provider` — `ModelProvider` interface, `OllamaProvider`, `ClaudeProvider` (LiteLLM SDK), routing table + `routing_profiles.yaml`, in-app daily budget, `model_call` logging, Instructor structured output, `FakeProvider` fixture.
- [x] `model-registry` — `model_registry` table, `scripts/models.py` (`list | search-hf | add | pull | bench | assign | rm`) supporting Ollama library, HF GGUF (→ Modelfile → `ollama create`), `mlx-community` snapshots; licence + disk tracking; `bench_model.py`.
- [x] `qdrant-repo` — `QdrantHybridRepository` (dense + sparse named vectors, fusion, payload filters, quantization), collection versioning, `reindex.py`, `SqliteHybridRepository` for tests.
- [x] `events-traces` — `events.emit`, verbs enum, `tutor_trace`/`retrieval_trace` writers, query helpers.
Benchmark `bench_stage0.py`: local `chat` ≥ 15 tok/s; one `grade_rubric` call routes to Claude and lands in `model_call` with cost; budget cap trips at the configured amount; a model downloaded from Hugging Face via `scripts/models.py pull` is benchmarked and assigned to `chat`; a 1k-chunk sample round-trips through Qdrant with a payload-filtered hybrid query.

## Stage 1 — One complete learning vertical slice (subject: attention mechanisms)
select concept → retrieve grounded material → teach → learner answers → assess → record evidence → update competency → schedule review.
- [ ] `seed-attention` — 6–10 `skill_node`s with prerequisites + `learning_object`s for attention (dot-product, scaled, multi-head, masking, positional encoding, KV cache) from 1–2 ingested sources (hand-ingested chunks OK).
- [ ] `context-packet` — builder with budgets + trace of drops.
- [ ] `tutor-turn` — orchestrator loop with kernel tools; SSE `/api/tutor/stream`; explicit mode; hint ladder; citations.
- [ ] `assess-evidence` — explain-back + cloze + MCQ; hierarchical grader; `competency_evidence` rows; `competency_state` refresh.
- [ ] `fsrs-memory` — `memory_state` via py-fsrs; due queue; minimum-viable review cap.
- [ ] `session-screen` — Home (mode + energy) → single-task session screen → review → recap with confidence. `ParkingLotButton`.
Benchmark `bench_stage1.py`: run 3 sessions on attention; every turn has a `tutor_trace`; every attempt yields evidence + FSRS update; delayed review 2 days later works; hard-check evals pass. **If this loop is not useful, stop and rethink — agents and voice will not fix it.**

## Stage 2 — Learning kernel, complete
- [ ] `skill-map` — whole-map-first Mermaid/interactive graph with competency + memory overlays (open learner model).
- [ ] `planner-v1` — rule-based block planner (session template, boundaries, early-switch with grasp check, movement placement, min-viable session).
- [ ] `preferences-checkpoints` — structured `learner_preference`, `session_checkpoint`, resume.
- [ ] `representations` — lazy render + cache of Representation kinds; "show it differently" flow.
- [ ] `challenge-modes` — planted-error, steelman, teach-back, calibration; each schedules a delayed item.
Benchmark: planner produces valid plans for all mode×energy combos; representation switch keeps object identity; resume from checkpoint mid-session.

## Stage 3 — Serious knowledge system
- [ ] `ingest-pipeline` — Udemy captions/slides/notebooks/PDFs → normalise → dedupe → semantic chunk → provenance → SQLite + Qdrant (dense + sparse); idempotent by content hash; `reindex.py`.
- [ ] `hybrid-retrieval` — server-side fusion, optional local reranker, trust/provenance filter, node/course payload filters; `retrieval_trace`.
- [ ] `retrieval-evals` — labelled queries, recall@k, citation coverage.
- [ ] `untrusted-content-guard` — tagged data blocks, instruction-pattern flagging, tests with poisoned chunks.
Benchmark: ≥ 5 courses ingested; recall@8 ≥ 0.8 on labelled set; poisoned-chunk tests pass; p95 search < 300 ms at current corpus size; Qdrant RAM < 1 GB.

## Stage 4 — Adaptive learning UX
- [ ] `adaptation-proposals` — observed pattern → proposal card (Try / Make default / No / Don't suggest again) → log → undo.
- [ ] `energy-planner`, `body-doubling`, `sensory-settings`, `models-settings-screen` (registry UI: search HF, download, bench, assign per task), `parking-lot-promote`, `soft-timers`.
- [ ] `experiments` — n-of-1 engine + dashboard (delayed recall, latency, error rate, completion, voluntary continuation, transfer).
- [ ] `domain-blocks` — language (spaced vocab), guitar, movement blocks with `practiced` events.
Benchmark: run one 2-week experiment (Socratic vs explicit on matched nodes) and read results.

## Stage 5 — Frontier models + voice
- [ ] `escalation-polish` — code review, conflicting-evidence resolution, deep explanation on Claude; prompt caching; cost dashboard.
- [ ] `voice-loop` — WS, Silero VAD, MLX Whisper, Kokoro persistent server, streaming playback, `spoke` latency events.
- [ ] `language-voice-block` — conversation practice; optional hosted realtime mode.
Benchmark: median ≤ 2 s to first audio over 20 turns.
(A throwaway `scripts/spike_voice.py` may be run any time earlier to de-risk the Mac stack.)

## Stage 6 — Offline / agentic intelligence & the learning system
- [ ] `offline-agents` — curriculum researcher, source comparison, exercise generation, KB maintenance, eval agents (Claude Code subagents / scripts, not the interactive tutor).
- [ ] `bandit-planner` — contextual bandit for representation/block choice; reward = delayed review outcome; shadow mode first.
- [ ] `dataset-export` — SFT/ORPO/KTO builders from events + preference pairs, retention-weighted.
- [ ] `mlx-finetune` — LoRA/QLoRA recipe + eval gate; only if Stage 4–5 evals show headroom.

## Thresholds that change the plan
ARCHITECTURE §8. Tripped → `/adr` first.

## Deferred
Cloud, auth, Tauri, LangGraph, Elasticsearch, Langfuse (optional compose profile), hosted realtime voice as default.
