# 0010 — Model registry: choose and download models (Hugging Face, Ollama library, MLX) per TaskClass
Date: 2026-09-19
Status: Accepted
## Context
The owner wants to pick and download different models (e.g. from Hugging Face) rather than a fixed list. Model names go stale monthly; routing must stay inspectable; local runtimes differ (Ollama wants GGUF or a Modelfile, MLX wants safetensors from `mlx-community`, whisper/Kokoro have their own artifacts).
## Decision
A `model_registry` table + `scripts/models.py` CLI (and later a Settings › Models screen) manage models: `id, display_name, source ∈ ollama_library|huggingface_gguf|huggingface_mlx|hosted, repo_id, file/tag, runtime ∈ ollama|mlx|hosted, role ∈ chat|code|embed|rerank|stt|tts|judge, quant, size_gb, context_len, status ∈ available|downloading|ready|failed, benchmark_json (tok/s, latency, quality-eval score), added_at`. Download paths: `ollama pull <tag>` for the Ollama library; `huggingface_hub.snapshot_download` of a GGUF file + generated Modelfile → `ollama create` for HF GGUF; `mlx-community/*` snapshot for MLX runtime. The routing table (`models_ai/routing.py`) references registry ids per `TaskClass`, and each TaskClass's assignment can be changed at runtime (persisted in `learner_preference` under `routing.<task>`), defaults ship in `routing_profiles.yaml`. Every download is followed by `scripts/bench_model.py` (tok/s, first-token latency, 5-case tutoring eval) whose results are stored in `benchmark_json` and shown before the model can be assigned. Hosted models are registry entries too (`source=hosted`, no download). Storage is under `data/models/` (gitignored); the registry tracks disk usage and can delete artifacts. Licences from the model card are recorded and shown.
## Consequences
+ Any HF/Ollama/MLX model can be tried and assigned per task without code changes; routing remains inspectable and logged on `model_call` (registry id + version). − Download/convert steps need Docker-free tooling (`huggingface_hub`, `ollama`, `mlx-lm`) and disk management; benchmarks are mandatory to avoid assigning an untested model.
## Alternatives considered
Hardcoded routing table (rejected: stale, not learner-controllable); LM Studio as model manager (optional GUI, not the source of truth).
## Evidence / sources
Owner request 2026-09-19; adaptive-learning report §C (MLX/Ollama serving and training paths).
