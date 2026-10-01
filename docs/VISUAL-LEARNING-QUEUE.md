# Visual learning, authoring and resource queue

Status: **assessment complete; implementation queued**, 2026-10-01. Finish the active Home resume slice first. This queue supplements the Q learning-experience plan and older reliability audit; it does not replace their unfinished work. No visual-kit application code, benchmark run, model pull, dependency, provider or migration has been activated.

## Assessment

The uploaded kit contains three proposals, six skills and one Python benchmark; it contains no ready-made UI assets or application components. Its source documents explicitly lack repository inspection. “Fixed decisions”, install commands and instructions to append AGENTS are proposal text, not accepted project policy. Originals are retained privately, unmodified. The implementation should use reconciled skills below rather than installing the six originals wholesale.

The useful direction is validated, versioned diagram data rendered locally; inline learner-controlled visual explanations; one-action capture of useful material; editable blocks; deterministic practice; and a small curated resource collection. Keep these capabilities inside existing lesson, area and playground flows.

### Existing code to reuse

| Capability | Actual integration point | Implication |
|---|---|---|
| Learning object / representations | `backend/app/db/models.py`, `kernel/representations.py`, `orchestrator/representations.py`, `api/representations.py` | Existing diagram is text (“Diagram in words”), not a stored typed visual. Representation cache can delete rows; immutable authored versions need distinct lifecycle semantics. |
| Grounding / routing | `orchestrator/context.py`, `models_ai/provider.py`, `gateway.py`, `ollama.py` | Reuse ContextPacket and task-specific routing/accounting; no production direct-Ollama shortcut. |
| Mermaid | `frontend/src/routes/Map.tsx`, package.json | Already dynamically imported with strict security; reuse pinned installed parser. Markdown component does not render Mermaid fences. |
| React Flow | `frontend/src/features/visualizer/BlockCanvas.tsx`, package.json | Library exists; audio graph domain/schema is not a curriculum graph. Share primitives only after mapping differences. |
| Authoring / correction | curriculum/areas APIs, CurriculumDraft, ContentReport, LearningObject | Reconcile draft/accept/publish and provenance rather than creating parallel course truth. |
| Trust / backup | numeric `trust_tier` in models, `db/backup.py`, `backup_crypto.py` | `learner_authored` is not an existing drop-in enum. Map origin separately from evidence quality and test full private backup inclusion. |
| Code practice | features/code, NotebookWorkspace and local lab | Browser sandbox and native Jupyter are different execution boundaries. Traces must not auto-run in the host kernel. |

### Corrections needed before implementation

1. **Confidence stays optional.** The kit's predict/reveal rule must not block controls or feedback on confidence. Creating content and accepting a diagram are not competency evidence.
2. **Repair budget is inconsistent.** Documents allow two repairs; benchmark supports one; browser render errors propose another. Define one server-owned total budget across schema and renderer failure, with idempotency, cooldown and request identity. Cancelled/stale callbacks cannot trigger further generation or overwrite drafts.
3. **The benchmark is a prototype.** Audited pure-validator probes show a non-object edge raises AttributeError and a flow without title/kind/version is accepted. It does not fully enforce the documented envelope. Eight passages, keyword overlap and approximate Mermaid lint cannot establish factual or pedagogical correctness. It also allows arbitrary host, raw output files, long timeouts and unbounded response reads. Do not select routes from it unchanged.
4. **Model measurement needs provenance.** Use shared production schemas, exact installed model digest/options, cold/warm timings, parser version and per-kind results. Include adversarial/malformed input and semantic review. Count failures/timeouts in denominators; record uncertainty. Synthetic summaries may be public, learner prompts/raw output stay private. No global CLI install or model download is needed to start assessment.
5. **Graph semantics vary.** Cycles are valid for feedback/state diagrams, disconnected concepts may be valid, and multiple correct orderings/equivalent labels need explicit handling. Topological reveal only applies to a DAG. Never invent relations solely to satisfy connectedness or a node minimum.
6. **Validated JSON is not automatically safe.** Ban arbitrary HTML/JS/SVG input, external loaders/links/actions and unbounded complexity. Mermaid strict mode and parse success do not establish correctness or eliminate all resource risks. Trusted renderer SVG is different from accepting raw authored SVG. New chart/template renderers need actual network-denial and input-bound tests. Vega-Lite supports both inline and URL data; constrain the supported subset and loader, not only top-level fields. [Vega-Lite data documentation](https://vega.github.io/vega-lite/docs/data.html).
7. **Resources are not offline just because metadata is local.** Curated cards work offline; their remote pages/players do not. Make any outbound load explicit. Even concept titles may contain private learner text, so use curated public search terms or a reviewed outbound query, not automatic title forwarding. Server URL fetching requires scheme/host/redirect/size/time bounds and protection against local-network requests.
8. **No promise of a recommendation-free player.** `rel=0` limits related videos to the same channel; it does not remove them. Use honest click-to-load/link behavior and a return-to-lesson action; do not claim the third-party player can be fully controlled. [Official player parameters](https://developers.google.com/youtube/player_parameters#rel).
9. **Licenses and availability remain gates.** Check exact versions, primary licenses, bundle impact and maintenance when a package/provider is actually selected. No LICENSE file was present in the archive; keep original code private while reuse rights are unresolved. Dependencies named in the kit are candidates, not approved installations. No need to adopt Markmap, Vega-Lite, Mafs, ELK or Excalidraw together.
10. **Resolve internal scope conflicts.** Excalidraw is optional in visuals but declared activated by authoring; indexing appears both early and optional later. Defer sketches/vision/indexing until their own decision. Keep editable topic areas primary; personal collections can organize authored work without returning to course silos.

## Implementable backlog

Every item below is **queued**, with dependencies and an observable completion gate. IDs avoid collisions with existing R/Q stages. Use one bounded commit per item; split further if needed. No issue tracker or separate app task was created.

| ID | Task / dependency | Completion evidence |
|---|---|---|
| V00 | Reconcile architecture and draft ADR; after current Home slice | Source ownership, tenant scope, immutable versions, kind selection and open decisions mapped; ADR remains proposed until accepted. |
| V01 | Harden benchmark; V00 | Shared typed validators; malformed shapes never crash; real installed Mermaid parser; bounded network/time/output; private raw output; synthetic regression tests. |
| V02 | Measure installed local models; V01 | Per-kind first-pass/final validity, semantic fidelity, repair cost and cold/warm latency; no automatic routing change; failing quality gate reported honestly. |
| V03 | Flow/Mermaid storage and generation; V00,V02 plus applicable ADR | Migration on disposable DB; learner-scoped APIs, validated versions, source versions, draft/accept/reject, global repair cap and failure/cancel tests. |
| V04 | Inline VisualBlock for flow/Mermaid; V03 | On-request render, keyboard/text equivalent, source references, reduced motion, narrow/zoom tests; stale repair cannot replace current visual. |
| A00 | Authoring reconciliation; V04 | Decide extension vs new models, origin/trust mapping, reference/version behavior, backup ownership and publication semantics. |
| A01 | Keep this + inbox; A00 | Capture exact answer/visual version with provenance and optional note, no navigation; duplicate/retry and storage failure tests; no mastery write. |
| A02 | Unit/block editor in learning areas; A01 | Markdown/visual blocks, keyboard reorder, stable IDs, versioning, draft restoration, preview identical to learning view. |
| E00 | Resource-provider contract; V04 | Public-term query policy, licenses, safe fetch/embed boundaries and disabled-provider tests mapped to current configuration. |
| E01 | Curated local resource cards; E00 | Reviewable seed candidates, at most three relevant cards, provenance/license fields, accept/reject; offline metadata and explicit external navigation; no auto-accept. |
| V05 | Node help and progressive reveal; V04 | Help uses node + exact source, questions opt-in; supported cycles handled; text/keyboard alternative, no autoplay. |
| V06 | Diagram exercises; V05 | Blank labels/order/missing-edge with deterministic bounded derivation, allowed equivalents/partial order, independent answer checks, dispute and stop/resume; optional confidence. |
| V07a–d | Outlines, charts, math templates, Python trace; V04 | One kind per slice. Each needs demonstrated lesson value, current license/bundle review, schema, bounded renderer, source-aware text equivalent and isolated journey. Pytrace executes only on Run in existing sandbox, caps steps/objects/time. |
| A03 | Authoring module templates; A02,V06 as relevant | Quiz/flashcards/order/labels/predict-reveal/code each has validator, editor, renderer and meaningful checker; no raw executable UI payload. |
| A04 | Images/sketches/export; A02 and dependency decision | Safe MIME/size/path handling, confirmed alt text, local asset references and export; measured lazy bundle impact; no image generation requirement. |
| A05 | Tutor-assisted blocks/questions/checks; A02 | Explicit request, grounded drafts, fallible check/dispute, clear authorship and no automatic publish. |
| A06 | Teach accepted authored units; A03,A05 | Preview and explicit publication, correct area linkage, review items idempotent; unpublish stops future scheduling but retains evidence. Indexing/trust decision explicit. |
| A07 | Portable export/import and backup; A02,A04/A06 as applicable | Versioned format, safe paths/size bounds, preserved assets/references/licenses, round-trip, duplicate import and encrypted private restore tests. No learner data in public seeds. |
| E02 | Optional licensed image providers; E01 | Exact API/license checks, outbound query review, attribution, quota/cache behavior, network-off fixtures. |
| E03 | Optional official video discovery; E01 | Key/config handling, quota-aware cache, honest click-to-load segmented playback and keyboard return; no promises to remove platform recommendations. |
| E04 | Optional search/page extraction; E01 and demonstrated gap | Reuse existing acquisition where appropriate; domain allowlist, safe redirects, explicit local/cloud choice, budget/privacy tests. No required new service. |
| V08 | Optional sketch/figure extraction/retrieval expansions; V04,A04 as applicable | Separate decision and evaluation for each; vision result remains unverified draft tied to source figure; accepted visual retrieval never self-validates generated claims. |

Suggested order when this queue becomes active: V00→V01→V02→V03→V04, A00→A01→A02, E00→E01, then the highest-value exercise/authoring branch. Do not launch every renderer/provider at once. Remaining Q reliability/clarity work is still open and should be coordinated in HANDOFF.

## Skills and execution prompts

New reconciled skills: `audhs-visual-specs` (data/render/exercises), `audhs-visual-benchmark` (measurement), `audhs-learner-authoring` (capture/publish/portability), `audhs-resource-curation` (curated and opt-in network resources). They complement existing learner-UX, state-reliability and tutor-evidence skills. They do not append the kit's AGENTS rules or install its generic skill names.

Use this prompt for any task:

```text
Implement task <ID> from docs/VISUAL-LEARNING-QUEUE.md after confirming its dependencies in the latest HANDOFF. Read current AGENTS.md, CLAUDE.md and applicable reconciled skill. Treat original kit paths/decisions as proposals. Reconcile current code, define the narrow user outcome and state ownership, then implement with synthetic fixtures and local-first execution. Preserve optional confidence, explicit-first teaching, source provenance, stop/resume and existing audio/comfort settings. Run relevant tests and required code/pedagogy review. Record exact evidence, model/manual limitations, rollback and next task. Follow existing private/public publication policy. Do not run later tasks, pull models, enable network providers or publish learner drafts implicitly.
```

Planning defaults: reuse local Mermaid and React Flow first; single-block drafts; curated metadata before network providers; sketches, vision, indexing and extra renderer dependencies deferred. These are queue recommendations, not accepted ADRs. Present concrete alternatives only when an implementation actually needs an unresolved choice.
