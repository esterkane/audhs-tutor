# Runtime extensions: evaluate benefit before adoption

Reviewed 2026-10-04. Status: investigation queue, not an accepted architecture replacement or provider activation. Existing local-first policy and task-specific hosted exceptions remain unchanged.

## Current baseline

The proposed Learning Kernel → Tutor Orchestrator separation already exists in `docs/ARCHITECTURE.md`. `backend/app/orchestrator/context.py` bounds learner/history/source context. `backend/app/models_ai/gateway.py` owns routing, reservations, fallback attempts and usage records. SQLite holds authoritative learner state and saved answers; Qdrant supplies source retrieval. Additions must solve a measured gap rather than create competing state owners.

## Ordered work

1. **Finish daily-learning acceptance.** Extend the existing isolated journeys for topic selection → explanation → notebook work → checked answer → stop/resume. Include source unavailable, storage denied, interruption, keyboard and narrow/zoom cases. Record physical audio and owner comprehension as separate manual evidence. Browser recordings do not establish comprehension.
2. **Tutor evaluation baseline.** Reuse the existing evaluation runner/results. Create versioned, reviewed scenarios for explanation before assessment, useful progressive hints, explicit versus Socratic mode, topic fidelity, exact learner-answer grounding, source citations, remembered corrections and stale-memory rejection. Include multi-session cases and deliberately incorrect prior answers. Keep held-out scenarios separate from prompt development. Report per-case failure, latency, tokens, provenance and cost; never infer human learning gains from synthetic performance.
3. **Memory comparison.** Compare current retrieval against a local Hindsight sidecar on the same reviewed scenarios. Use synthetic data first, pin the release and verify deployment/license requirements. Assess memory precision, contradiction handling, correction/deletion propagation, source-version freshness, retrieval latency and total resource cost. Inferred memories are advisory context with source IDs, timestamps and uncertainty; they cannot write competency, FSRS or preferences. No production migration unless benefit exceeds the operational cost and an ADR is accepted.
4. **Voice comparison.** Preserve local recognition/synthesis as default. Benchmark optional Groq and a separate Gemini Live reference against local voice with matched content and recorded conditions. Measure end-of-utterance to first audio, p50/p95, recognition errors, interruption recovery, answer quality, failures and cost. Do not equate model throughput with conversation latency. Hosted experiments require explicit task-scoped configuration, permitted test audio and a spend limit; no silent upload/fallback. The owner's personal voice gate remains separate.
5. **Development tooling.** Antigravity is an optional authoring/testing tool, not an app runtime dependency. Compare one bounded sandbox journey with the existing Playwright/browser workflow. Assess defect detection, reproducibility and accessibility evidence, not generated-code volume. Never run two coding agents on overlapping files or personal learner records.
6. **Hosted gateway, only if needed.** Cloudflare AI Gateway remains deferred while the local application gateway meets requirements. Before adoption, document incremental value, data processing/retention, payload logging, cost, outages, retry amplification and idempotency. Preserve application budget enforcement and one learning write per request. An edge gateway must not independently retry a non-idempotent assessment or silently choose a new data destination.

## Tool-specific findings and boundaries

- [Hindsight](https://github.com/vectorize-io/hindsight) supports retain/recall/reflect and local model providers, with its own storage/runtime infrastructure. It is a candidate implementation of advisory longitudinal retrieval, not the source of truth for learning state.
- [Groq speech recognition](https://console.groq.com/docs/speech-to-text) is hosted. Its documented API is a candidate benchmark path, not proof that this Mac's end-to-end voice loop improves.
- [Gemini Live](https://ai.google.dev/gemini-api/docs/live-api) supplies streaming voice/vision interaction. Evaluate it as a reference experience before integrating it with tutoring policy and persistent state.
- [Antigravity browser tooling](https://www.antigravity.google/docs/browser) provides browser actions and artifacts. A new IDE does not itself establish accessibility or pedagogy quality.
- [Cloudflare logging controls](https://developers.cloudflare.com/ai-gateway/observability/logging/) distinguish payload storage from metadata logs. Disabled payload logging does not make a hosted request local.
- If the proposed Magpie means [magpie-align/magpie](https://github.com/magpie-align/magpie), it synthesizes instruction data, rather than providing a validated learner simulation. Use only to propose candidate test scenarios with independent review. Confirm identity before installing a different similarly named tool.
- Mixboard, WanGP, Spline and PersonaPlex are not selected or evaluated by this review. Keep them outside the critical path until a specific learner need, local hardware/export requirement and acceptance test are identified.

## Completion evidence

Each experiment records baseline and candidate versions, scenario IDs, reproducible command, raw results, known limitations and adopt/defer/reject rationale. Passing API compatibility, an attractive demo or a vendor benchmark is insufficient. Adopt only after a reviewed measurable improvement without regression in local control, learner agency, source fidelity and recovery behaviour.
