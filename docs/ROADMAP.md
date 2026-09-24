# Roadmap

**Current stage:** 4 — Adaptive learning UX **done 2026-09-19** (benchmark 5/5; the two-week experiment is simulated — run it for real) → next: Stage 5 (frontier models + voice)

Order follows the Architecture Review Brief: prove the learning loop first, then the kernel, then the knowledge system, then adaptive UX, then frontier+voice, then offline agents. Each stage: slices (`/feature-slice`), a benchmark script, exit criteria.

## Cross-course learning areas — 2026-09-24

- [x] Editable area organization, local bounded drafts, source provenance, question ratings and reversible preference suggestions. See `docs/slices/knowledge-areas.md` and ADR-0015.
- [ ] Expand evaluated coverage beyond small passage samples; validate cross-source synthesis and learning outcomes in actual use.

## Stage 0 — Skeleton (½ day)
- [x] `repo-bootstrap` — `scripts/bootstrap.sh`, Makefile, `.env.example`, uv + pnpm projects, ruff/prettier, Qdrant container (`make services`).
- [x] `db-core` — ORM + Alembic for all Phase-1 tables (ARCHITECTURE §4); `learning_event` append-only; `learner_id` everywhere; export/wipe scripts + test.
- [x] `model-provider` — `ModelProvider` interface, `OllamaProvider`, `ClaudeProvider` (LiteLLM SDK), routing table + `routing_profiles.yaml`, in-app daily budget, `model_call` logging, Instructor structured output, `FakeProvider` fixture.
- [x] `model-registry` — `model_registry` table, `scripts/models.py` (`list | search-hf | add | pull | bench | assign | rm`) supporting Ollama library, HF GGUF (→ Modelfile → `ollama create`), `mlx-community` snapshots; licence + disk tracking; `bench_model.py`.
- [x] `qdrant-repo` — `QdrantHybridRepository` (dense + sparse named vectors, fusion, payload filters, quantization), collection versioning, `reindex.py`, `SqliteHybridRepository` for tests.
- [x] `events-traces` — `events.emit`, verbs enum, `tutor_trace`/`retrieval_trace` writers, query helpers.
Benchmark `bench_stage0.py`: local `chat` ≥ 15 tok/s; one `grade_rubric` call routes to Claude and lands in `model_call` with cost; budget cap trips at the configured amount; a model downloaded from Hugging Face via `scripts/models.py pull` is benchmarked and assigned to `chat`; a 1k-chunk sample round-trips through Qdrant with a payload-filtered hybrid query.
**Measured 2026-09-19** (`make bench s=0`, M4 Pro 48 GB; raw in `evals/results/bench_stage0.json`):
- A local `chat` (llama31-8b, Ollama): **47.5 tok/s** — PASS (≥ 15)
- B `grade_rubric` → Claude with cost: **SKIP** (no `ANTHROPIC_API_KEY`); mechanism covered by `tests/test_model_provider.py`
- C budget cap $0.25: calls primary $0.20 → primary $0.20 → **degraded** (local, $0) — PASS
- D HF pull: `Qwen/Qwen2.5-0.5B-Instruct-GGUF` q4_k_m (0.49 GB, apache-2.0) → `ollama create` 15 s → bench **272.8 tok/s**, first token 85 ms, tutoring hard checks 0.73 → assigned to `chat`, then routing restored to llama31-8b — PASS
- E 1000 synthetic chunks → Qdrant (nomic-embed-text 768d + BM25 sparse, RRF): index 6.9 s, filtered hybrid queries 20/20 correct, search p50 **26 ms** / p95 **30 ms** — PASS

## Stage 1 — One complete learning vertical slice (subject: attention mechanisms)
select concept → retrieve grounded material → teach → learner answers → assess → record evidence → update competency → schedule review.
- [x] `seed-attention` — 6–10 `skill_node`s with prerequisites + `learning_object`s for attention (dot-product, scaled, multi-head, masking, positional encoding, KV cache) from 1–2 ingested sources (hand-ingested chunks OK).
- [x] `context-packet` — builder with budgets + trace of drops.
- [x] `tutor-turn` — orchestrator loop with kernel tools; SSE `/api/tutor/stream`; explicit mode; hint ladder; citations.
- [x] `assess-evidence` — explain-back + cloze + MCQ; hierarchical grader; `competency_evidence` rows; `competency_state` refresh.
- [x] `grading-evidence` — semantic review before free-text credit; exact criterion coverage; retryable failures preserve learning state and answers. Fake-provider and UI checks: 333 backend / 44 frontend; live semantic accuracy remains unmeasured.
- [x] `lesson-activation-ui` — course → section → readable review → explicit local activation; secondary controls collapsed, sources inline, unsaved-edit and refreshed-version safeguards.
- [x] `fsrs-memory` — `memory_state` via py-fsrs; due queue; minimum-viable review cap.
- [x] `session-screen` — Home (mode + energy) → single-task session screen → review → recap with confidence. `ParkingLotButton`.
Benchmark `bench_stage1.py`: run 3 sessions on attention; every turn has a `tutor_trace`; every attempt yields evidence + FSRS update; delayed review 2 days later works; hard-check evals pass. **If this loop is not useful, stop and rethink — agents and voice will not fix it.**
**Measured 2026-09-19** (`make bench s=1`, isolated `data/bench.db`, llama3.1:8b as fallback for explain/hint because `gemma3:12b` is not pulled; raw in `evals/results/bench_stage1.json`):
- A every turn has a `tutor_trace` with `model_call` + `retrieval_trace`: 6/6 — PASS
- B every attempt → `competency_evidence` + `review_log` (FSRS): 9/9, 6 competency states — PASS
- C delayed review: one wrong MCQ → due within 1 min, 4 items due at +2 days; rating Good then raised stability by 2.22 — PASS
- D hard-check evals (`scripts/run_evals.py`, 5 cases): **4/5 = 0.8** — PASS (threshold 0.75). Passing: explain with `[n]` citation, hint-first, recap within 5 sentences, negated full-solution. Failing: `socratic-masking` (the 8B model explains instead of asking one narrowing question). Before the code-review fix that restored the dropped output-contract sections (`instructions`, `hint_level`, `socratic_rule`) the rate was 0.4; baseline committed as `evals/results/baseline.json`.
- E loop signal: 3 sessions moved vec-dot-product 0.71 → softmax 0.60 → attn-dot-product 0.50 (unlock gate works); turn latency p50 ≈ 6 s, max 10 s — PASS
- Verdict on "is this loop useful": yes. Retrieve → teach with citations → confidence → grade → evidence → FSRS → next node works end to end on a local 8B model. Socratic mode needs a stronger local model (`gemma3:12b`, the plan's default) or a hosted fallback.

## Stage 2 — Learning kernel, complete
- [x] `skill-map` — whole-map-first Mermaid/interactive graph with competency + memory overlays (open learner model).
- [x] `planner-v1` — rule-based block planner (session template, boundaries, early-switch with grasp check, movement placement, min-viable session).
- [x] `preferences-checkpoints` — structured `learner_preference`, `session_checkpoint`, resume.
- [x] `representations` — lazy render + cache of Representation kinds; "show it differently" flow.
- [x] `challenge-modes` — planted-error, steelman, teach-back, calibration; each schedules a delayed item.
Benchmark: planner produces valid plans for all mode×energy combos; representation switch keeps object identity; resume from checkpoint mid-session.
**Measured 2026-09-19** (`make bench s=2`, isolated `data/bench2.db`, llama3.1:8b; raw in `evals/results/bench_stage2.json`):
- A planner: 90 mode × energy × due × preference combos, all pass `validate_plan`; deterministic — PASS
- B representations: analogy + derivation rendered for the same LearningObject → identical `object_id`; the repeat request came from cache (same representation id, 2 model calls total) — PASS
- C resume: hint turn → UI checkpoint (phase=assess, block 2) → fresh DB session reads skill, phase, hint level 1, block index — PASS
- D challenge: the model planted a real conceptual error ("1/sqrt(d_k) is a learned parameter"), graded against the hidden key by the local grader (score 0 for a canned answer that named a different error), delayed item due at +2 days — PASS
- Not yet exercised by the benchmark: the plan strip in the UI (checked manually in the browser pane), block events over HTTP (covered by `tests/test_stage2_api.py`).

## Stage 3 — Serious knowledge system
- [x] `ingest-pipeline` — Udemy captions/slides/notebooks/PDFs → normalise → dedupe → semantic chunk → provenance → SQLite + Qdrant (dense + sparse); idempotent by content hash; `reindex.py`.
- [x] `hybrid-retrieval` — server-side fusion, optional local reranker, trust/provenance filter, node/course payload filters; `retrieval_trace`.
- [x] `retrieval-evals` — labelled queries, recall@k, citation coverage.
- [x] `untrusted-content-guard` — tagged data blocks, instruction-pattern flagging, tests with poisoned chunks.
- [x] `n8n-workflows` (2026-09-23) — built-in bounded JSON workflow reader; graph structure and teaching notes, no execution or parameter values; archive provenance and repeat-import tests.
- [x] `ingest-formats` (2026-09-20) — every common course format with stdlib parsers: Office (docx/pptx/xlsx), ODF, EPUB, HTML, RTF, LaTeX, rst/org/adoc, 30+ source languages (secrets redacted), zip/tar archives (zip-slip guard, `<archive>!/<member>` URIs), transcript formats (SBV, ASS, TTML, Whisper/json3 JSON, TSV, timestamped text); `GET /api/corpus/capabilities`, `scripts/ingest.py --capabilities`.
- [x] `media-transcription` (2026-09-20) — audio/video → timed chunks via the registry STT model (`TaskClass.STT`, `whisper-large-v3-turbo` on MLX, ffmpeg or macOS afconvert, sidecar captions win, transcript cache by content hash), slide images via the registry vision model (`TaskClass.VISION`, `gemma3-12b`); each call logged in `model_call`.
Benchmark: ≥ 5 courses ingested; recall@8 ≥ 0.8 on labelled set; poisoned-chunk tests pass; p95 search < 300 ms at current corpus size; Qdrant RAM < 1 GB.
**Measured 2026-09-19** (`make bench s=3`, isolated `data/bench3.db` + throwaway collection `corpus_v903`, nomic-embed-text 768d + BM25, no reranker; raw in `evals/results/bench_stage3.json`):
- A ingest: 5 courses (`seeds/courses`: VTT, SRT, ipynb, markdown, text) → 17 documents, 34 chunks in 0.9 s, 0 duplicates, 0 flagged; forum dump at trust 0 → 1 chunk, flagged; re-run → 0 new versions, 0 re-indexed; index count = 35 — PASS
- B recall@8 on 32 labelled queries: **1.000** (recall@4 1.000, recall@1 0.906, MRR 0.948, citation coverage 0.961; the misses at k=1 are neighbouring sections of the right lecture) — PASS (≥ 0.8). Corpus is small; `make eval-retrieval` re-measures against any DB/collection and fails on a > 0.05 regression vs `evals/results/retrieval_baseline.json`
- C poisoned-chunk tests (`tests/test_untrusted_guard.py` + data-block test, end-to-end through `TutorTurn` and the grader): 5/5 — PASS
- D hybrid search latency, 96 searches: p50 **29 ms**, p95 **35 ms**, max 37 ms — PASS (< 300 ms)
- E Qdrant RAM: `memory_active_bytes` **0.34 GB** (docker stats 624 MiB incl. container overhead) — PASS (< 1 GB)
- After the kit reviews (pedagogy-reviewer: ship-with-fixes → 7 fixes applied; code-reviewer: 17 findings → all majors and most minors applied): backend 96 tests, frontend 11, bench re-run 5/5, tutoring hard checks 4/5 (= Stage 1 baseline).
- **With the reranker** (`ms-marco-minilm-l6` pulled by the owner, 82 ms / 16 docs × 800 chars): B recall@1 0.906 → **0.938**, MRR 0.948 → **0.964**; D p50 121 ms / p95 **129 ms** — still PASS. Real corpus (`~/Downloads/Udemy Resources`, one course with 67 notebooks/PDF → 156 unique chunks + 89 duplicates dropped; two `.docx` skipped): dev corpus 294 chunks, `make eval-retrieval` recall@8 1.000 / recall@1 0.844 / MRR 0.911, p95 183 ms. `pypdf` added (owner approved). Backend 98 tests.
- Superseded note (kept for history): the benchmark run itself used no reranker and only the five sample courses; the reranker, `pypdf` and the real Udemy export were measured afterwards — see the two bullets above and the formats follow-up below.
- **Formats follow-up, measured 2026-09-20** (scratch DB, `--no-index`, whole `~/Downloads/Udemy Resources`): 5282 files → **5086 documents** (both `.docx` parsed; the 7328-file `agents-main.zip` expanded in place: notebooks, code, markdown), 13 809 chunks, 2036 duplicates dropped, 431 flagged; 196 skipped with a reason each (101 images — no vision model pulled; 30 audio/video — no STT model pulled; 26 `.env*`/key files; 33 dataset/config JSON; 3 broken notebooks). Re-run: 5086 unchanged, 0 new. Backend 44 ingest tests (20 + 24 new), frontend Corpus test extended. Not measured: real Whisper/vision output (models not pulled — owner decision, see HANDOFF).

## Stage 4 — Adaptive learning UX
- [x] `adaptation-proposals` — observed pattern → proposal card (Try / Make default / No / Don't suggest again) → log → undo.
- [x] `energy-planner`, `body-doubling`, `sensory-settings`, `models-settings-screen` (registry UI: search HF, download, bench, assign per task), `parking-lot-promote`, `soft-timers` (`docs/slices/adaptive-ux-bundle.md`).
- [x] `experiments` — n-of-1 engine + dashboard (delayed recall, latency, error rate, completion, voluntary continuation, transfer).
- [x] `domain-blocks` — language (spaced vocab), guitar, movement blocks with `practiced` events.
Benchmark: run one 2-week experiment (Socratic vs explicit on matched nodes) and read results.
**Measured 2026-09-19** (`make bench s=4`, isolated `data/bench4.db`, llama3.1:8b; raw in `evals/results/bench_stage4.json`). A real two-week run needs the owner's sessions; the benchmark runs the identical pipeline with time travel over 14 simulated days:
- A adaptation card: 8 attempts with 3 hints each on an unmastered skill → `hint_heavy` card ("Start new material with a worked example (for skills you have not yet mastered)" / "You used 3.0 hints per attempt over the last 8 attempts on unmastered skills.") → Try applied `worked_example` (origin proposed_accepted) → next session expired it (1 undone, pref restored) → events proposed/decided/adapted/undone — PASS
- B two-week Socratic vs explicit on six matched attention nodes (each node taught by the real local model in its assigned arm on day 0/2/…/10, assessed, its cards reviewed two days later; delayed recall counts only reviews ≥ 1 day after the previous review): assignment balanced 3/3, 18 arm-stamped events, results readable on the dashboard. Delayed recall explicit 1.00 (n=3) vs socratic 1.00 (n=3), difference 0.000, 95 % CI 0.000 to 0.000 → reading "No clear difference yet … Keep going or stop: your call." Error rate 0/0, latency 4000/4000 ms (canned), completion / continuation / transfer "not enough data" (no block events in the simulation). The pipeline is proven; the *answer* needs the owner's real two weeks — PASS on mechanism, not on the hypothesis.
- C energy check-in: plan 51 min → re-plan at energy 1 = 34 min as a card → Try applied to the session's blocks → Undo restored the original plan — PASS
- D domain blocks: 3 German cards due → planned `domain_switch(domain=language, 11 min)`; the AI/ML review contained no vocab; all 3 reviewed in the language block → 0 left; guitar `practiced` event logged; movement skipped 3× → `movement_skipped` card — PASS
- After the kit reviews (pedagogy-reviewer: ship-with-fixes, 9 fixes applied; code-reviewer: 3 blockers + 7 majors + minors, all blockers/majors and most minors applied — see the slice docs' "Review fixes"): backend 122 tests, frontend 18, bench re-run 5/5.
- E models registry: routing table resolves 18 of 20 task classes to ready models (chat/hint/… → llama31-8b, embed → nomic-embed-text, rerank → ms-marco-minilm-l6); `grade_rubric` and `judge` unresolved until an API key exists — PASS

## Stage 5 — Frontier models + voice
- [x] Optional OpenAI provider: separate credentials, accounted benchmarks, typed/streamed replies and synthetic compatibility evidence (`slices/openai-provider.md`). Local task defaults unchanged; broader tutoring/grading quality acceptance remains open.
- [ ] `escalation-polish` — code review (a first Pyodide code exercise landed in P8 2026-09-20 — `docs/slices/code-exercise.md`; hosted `code_review` still needs the key), conflicting-evidence resolution, deep explanation on Claude; prompt caching; ~~cost dashboard~~ (cost view + reservation-based budget + per-attempt usage accounting done in P6 2026-09-20, `docs/slices/usage-accounting.md`; the hosted TaskClasses themselves still need `ANTHROPIC_API_KEY`).
- [ ] `voice-loop` — WS, Silero VAD, MLX Whisper, Kokoro persistent server, streaming playback, `spoke` latency events. **Implemented with fakes in P9 (2026-09-20, `docs/slices/voice-loop.md`)**: setup lifecycle, WS loop with cooperative interruption, text fallback, retention opt-in, `spoke` events, `scripts/spike_voice.py`, `scripts/bench_voice.py`. Unticked because the benchmark gate and an ADR (TaskClass.TTS, Kokoro server instead of MLX TTS) are pending: no Whisper snapshot / `mlx-whisper` / Kokoro server installed here; the 20-turn benchmark refuses to run until they are.
- [ ] `language-voice-block` — conversation practice; optional hosted realtime mode. (Guided *listening* landed in P7; spoken conversation practice inside the language block landed in P9 2026-09-20 — `docs/slices/language-voice-block.md`, practice-only, logged as `practiced`; hosted realtime not started — paid, unauthorised.)
Benchmark: median ≤ 2 s to first audio over 20 turns.
(A throwaway `scripts/spike_voice.py` may be run any time earlier to de-risk the Mac stack.)
**Measured 2026-09-21 — evidence, not the gate** (`scripts/bench_voice.py --wavs … --transcripts … --dataset "LibriSpeech dev-clean …"`, disposable DB, hosted providers off; M4 Pro 48 GB; whisper-large-v3-turbo (MLX) → `llama31-8b` (Ollama, the profile's `chat` route) → Kokoro-82M in the CPU Docker image; raw in `evals/results/bench_voice.json`). Audio: 50 LibriSpeech dev-clean utterances (speakers 1272 + 2277, CC BY 4.0, English read speech, 2–29 s, median 5.8 s) — **not the owner's voice**, so ADR-0011's "≥ 20 own recordings" gate stays open; the script marks the run `own_recordings: false` and exits non-zero.
- Recognition: 25/25 turns, 0 failures, **WER median 0.0, mean 3.2 %** (worst utterance 10 %).
- Latency to first audio, measured the way `voice/loop.py` works (TTS starts at the first sentence boundary while the LLM keeps streaming): **median 2.30 s, p95 2.94 s — target ≤ 2 s narrowly missed.** Stage medians: STT 0.83 s · LLM first token 0.13 s · first sentence complete at 1.26 s after utterance end · synthesis of that sentence 1.04 s (pure Kokoro time, measured from its own request) · LLM generation to the end 0.58 s (overlaps the TTS, off the critical path).
- **Measured, not projected (later the same day):** `voice/loop.py` now starts speaking at the first closed clause of the first sentence (`speech_chunks`, preference `voice.early_speech`, default on, reversible), and `bench_voice.py --first-clause` reproduces that decision. Back-to-back runs on the same 25 utterances: **first-clause median 1.97 s, p95 2.55 s** vs sentence-start median 2.45 s, p95 3.14 s (`evals/results/bench_voice_first_clause.json` / `bench_voice.json`). The clause seam buys 0.3–0.5 s (the sentence baseline itself moved 2.30 → 2.45 s between runs); the median now sits at the 2 s target, the p95 does not. Run-to-run variance is ≈ ±0.15 s on the median (an earlier sentence-mode run measured 2.30 s).
- An earlier run the same day (first measurement, since corrected) had conflated remaining LLM generation with TTS time; those numbers are superseded by the above.
- Still needed for the gate: the owner's own short utterances (`--own-recordings`), which also better match conversation turns than LibriSpeech's read paragraphs (STT time scales with utterance length).

## Stage 6 — Offline / agentic intelligence & the learning system
- [ ] `offline-agents` — curriculum researcher, source comparison, exercise generation, KB maintenance, eval agents (Claude Code subagents / scripts, not the interactive tutor).
- [ ] `bandit-planner` — contextual bandit for representation/block choice; reward = delayed review outcome; shadow mode first.
- [ ] `dataset-export` — SFT/ORPO/KTO builders from events + preference pairs, retention-weighted.
- [ ] `mlx-finetune` — LoRA/QLoRA recipe + eval gate; only if Stage 4–5 evals show headroom.

## Thresholds that change the plan
ARCHITECTURE §8. Tripped → `/adr` first.

## Deferred
Cloud, auth, Tauri, LangGraph, Elasticsearch, Langfuse (optional compose profile), hosted realtime voice as default.

## Playground extension — 2026-09-24

- [x] Initial Python playground and guided pipeline practice; implementation checks pass (see `slices/playground.md`).
- [ ] Tutor correctness gate: local debugging failure remains; evaluate the selected hosted candidate.
- [ ] Interactive workflow builder and real LangChain/n8n integrations.
