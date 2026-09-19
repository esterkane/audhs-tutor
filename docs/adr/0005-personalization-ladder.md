# 0005 — Personalization ladder; fine-tuning gated by evals
Date: 2026-09-19
Status: Accepted
## Context
The owner wants "a system that learns" and preparation for fine-tuning a local model. n=1 fine-tuning risks overfitting and sycophancy; satisfaction is a misleading target.
## Decision
Ascending-cost ladder: (1) prompt-based learner profile + memory; (2) RAG over own history; (3) contextual bandit for representation/block choice with reward = delayed FSRS review outcome; (4) LoRA/QLoRA SFT on MLX (Qwen/Gemma/Llama 7–14B) from logged transcripts; (5) ORPO/KTO on logged preference pairs. Steps 4–5 only if step-3 evals show headroom and a held-out retention-proxy eval improves. Log everything needed from day one (docs/EVENT-SCHEMA.md).
## Consequences
+ Cheap wins first; data ready for later. − Requires disciplined event logging now.
## Alternatives considered
Fine-tune early (rejected: no data, sycophancy risk).
## Evidence / sources
docs/research/adaptive-learning-report.md §C.
