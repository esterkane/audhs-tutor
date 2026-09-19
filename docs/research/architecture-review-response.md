# Response to the Architecture Review Brief (2026-09-19)

Verdict: the brief's central principle (LLM proposes; deterministic kernel decides) is correct and is now ADR-0007. Item-by-item:

| # | Brief item | Verdict | What changed / why |
|---|---|---|---|
| 1 | Kernel / Orchestrator separation | Correct | Adopted (ADR-0007). Kernel tools are typed and deterministic; orchestrator is one loop. |
| 2 | CompetencyState ≠ MemoryState | Correct, with a caveat | Adopted (ADR-0004). Caveat: four stored sub-scores at n=1 is false precision → scores are a *view* over evidence rows with count, decay and confidence. FSRS retrievability feeds only the recall dimension. |
| 3 | LearningObject | Correct; risk of premature abstraction | Adopted with a minimal field set; representations rendered lazily and cached. VR = renderer, no backend change. |
| 4 | FTS5 + sqlite-vec + RRF | Rejected by owner | Owner wants Qdrant from day one (50–200-course corpus, filtered hybrid search, ES-like mental model). `RetrievalRepository` interface stays binding; Qdrant is the production adapter; SQLite hybrid kept for tests/offline fallback (ADR-0002). |
| 5 | Provenance + poisoned RAG | Correct | Adopted structurally (ADR-0008): tagged data blocks, never system role, flagged patterns, poisoned-chunk tests. |
| 6 | ContextPacket + three stores | Correct | Adopted (ADR-0007). Session checkpoint is a table with TTL, not a file. |
| 7 | Single orchestrator | Correct | Multi-agent only for offline Stage-6 work (Claude Code subagents/scripts). |
| 8 | Hierarchical grading | Correct | ADR-0009. Added weight-by-grader-level when converting to evidence. |
| 9 | Propose/accept adaptation | Correct | Already in invariants; strengthened with the 4-option proposal card and "no AuDHD ⇒ X assumptions". |
| 10 | Observability incl. learning outcomes | Correct | Traces in SQLite from day one; Langfuse becomes an optional compose profile. |
| 11 | Ollama + FastAPI + SQLite | Correct | LiteLLM proxy dropped in favour of the SDK behind `ModelProvider` (ADR-0001). |
| 12 | Simplify for solo dev | Mostly | One container (Qdrant) in Phase 1, nothing else. Pushback: keep `ClaudeProvider` from Phase 1 for rubric grading (a local 12B is unreliable there); allow a throwaway voice spike script early because the owner wants voice and it de-risks the Mac stack. |

Weaknesses the brief missed
- Multi-user migration: `learner_id` on every table now, ULIDs, no singletons — cheaper than retrofitting.
- Prompt caching layout: the byte-stable policy prefix must come first in the ContextPacket or Anthropic caching is lost.
- Budget enforcement moves in-app when the proxy goes; it needs a test.
- The competency refresh must be idempotent and re-runnable after re-weighting evidence (no stored truth in `competency_state`).
- Retrieval evals (recall@k on labelled queries) are as important as tutoring evals; added to Stage 3.
