# Slice: model-registry (Stage 0)

**Story.** The learner can find, download, benchmark and assign any Hugging Face / Ollama / MLX model per TaskClass without code changes; nothing is assigned untested (ADR-0010).
**In/out.** `scripts/models.py` (`seed | list | search-hf | info | add | pull | bench | assign | rm`, runs via `make models args="…"`); `models_ai/downloader.py` (Ollama `/api/pull` streaming, HF GGUF → Modelfile → `ollama create <registry id>`, `mlx-community` snapshots, licence + size from `HfApi.model_info`, artifact removal under `data/models/`); `models_ai/bench.py` (tok/s + first-token ms from Ollama's own counters, 5-case tutoring hard checks: ≤ 6 sentences, no banned language, check question/next step) → `benchmark_json`; `registry.assign` writes `learner_preference routing.<task>` and refuses non-ready or unbenchmarked rows.
**Events.** None (registry changes are not learning events); every later call logs `registry_id` on `model_call`.
**Permissions.** `pull`/`rm`/`ollama create` stay in the *ask* list; downloads are learner-initiated.
**Verified by.** `tests/test_model_registry.py` (slug/Modelfile/size, hard checks, bench with FakeProvider + storage, HF-GGUF spec mapping, CLI contract) and the Stage 0 benchmark (real HF pull → bench → assign).
