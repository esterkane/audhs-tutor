# Slice: context-packet (Stage 1)

**Story.** Every tutor turn gets a bounded, inspectable context: the byte-stable policy first, then structured per-turn sections, retrieved chunks as quoted data, and an explicit output contract. What did not fit is logged, never silently lost.
**In/out.** `orchestrator/context.py`: `SectionBudget` (tokens ≈ chars/4; preferences 300, session 150, contract 400, evidence 300, retrieved 1800, request 400, contract 200), `build_packet()` drops dict keys from the end / lowest-ranked chunks first and records `dropped[]` + `section_tokens{}`; `data_block()` wraps chunks in `<retrieved_data note=…>` with `[n] source=… trust_tier=… flags=…` headers and escaped angle brackets; `learner_answer_block()` for graders; `render_messages()` = system(policy) + one user message in fixed section order. `orchestrator/prompts.py` loads versioned files (`PROMPT_VERSION = pedagogy.v1+tutor.v1`).
**Traces.** `tutor_trace.sections_json` / `dropped_json` come straight from the packet.
**Security (ADR-0008).** Retrieved text never enters the system role; instruction-like patterns are flagged on the chunk and shown in the block header; the policy states data blocks are quoted material.
**Verified by.** `tests/test_orchestrator.py::test_packet_budgets_drop_lowest_ranked_and_log`, `::test_data_block_escapes_and_flags_poison`.
