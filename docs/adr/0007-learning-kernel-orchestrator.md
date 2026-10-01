# 0007 — Learning Kernel owns state; one Tutor Orchestrator; LearningObject/Representation; bounded ContextPacket
Date: 2026-09-19
Status: Accepted
## Context
An LLM that owns learner, curriculum, memory or truth state is unauditable and drifts. Multi-agent tutoring adds cost and failure modes without evidence of benefit for a single learner. Conversation-dumping as memory is expensive and noisy.
## Decision
Deterministic Learning Kernel (`backend/app/kernel/`) owns skill graph, LearningObjects, competency, memory, session/checkpoint/preferences, planner, adaptation proposals, experiments. One Tutor Orchestrator (`backend/app/orchestrator/`) runs the turn loop with typed kernel tools; the LLM proposes explanations, questions, feedback and interpretations only. Content is modelled as `LearningObject` (source of truth) rendered into `Representation`s lazily and cached; "show it differently" changes the representation. Every turn assembles a bounded `ContextPacket` (policy, preferences, session state, learning contract, evidence, retrieved knowledge as tagged data, request, output contract) with per-section budgets; the full chat history is never the context. Three stores: append-only event log (audit), session checkpoint (temporary), structured learner state (durable). Observability tables (`tutor_trace`, `retrieval_trace`, `model_call`) are written from day one; Langfuse is optional. Multi-agent work is reserved for offline tasks (Stage 6). Every learner-scoped table carries `learner_id`; repositories sit behind interfaces; no module singletons.
## Consequences
+ Auditable decisions, cheap context, clear migration path (Postgres/pgvector/Qdrant are adapter swaps). − More explicit code than a chat loop; the kernel needs its own tests.
## Alternatives considered
LLM-with-memory chat loop; LangGraph multi-agent tutor; per-modality content models.
## Evidence / sources
Review brief §1–4, §8–9, §17–18; adaptive-learning report §A (Bridge: expert decisions conditioning).
