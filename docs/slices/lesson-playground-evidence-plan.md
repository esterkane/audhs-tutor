# Lesson-grounded coding tutor: next C3 contract

2026-10-04. Implementation plan, not a completed capability.

## Verified current boundary

The lesson-linked Playground supplies goal text and a navigation target, isolates drafts by session/skill and rechecks the origin client-side before fresh sends/retries. `schemas/playground.py` correctly labels learning_context as client navigation metadata. `orchestrator/playground.py:respond` checks session ownership/end state, then may reuse an exact saved answer before generating. It does not validate a typed lesson origin or retrieve lesson sources; saved metadata explicitly has sources=[] and supplied_workspace_only. `db/answer_memory.py` compares supplied work and navigation identity, not source versions. This is honest general coding help, but insufficient for source-grounded lesson examples.

The main tutor already retrieves through tools.retrieve with server skill/course filtering, writes retrieval traces, and stores source hashes. Reuse that interface and existing provenance types rather than introducing another vector store or trusting client-provided labels as evidence.

## Next bounded changes

1. **Typed origin and server validation.** Add an optional explicit lesson-origin object to PlaygroundRequest (skill identity; session already exists). Preserve standalone/program/saved-answer callers. Resolve ownership, current checkpoint and skill on the server before any new model work. Do not overload target_id string parsing as authorization. Frontend sends the origin only for the verified lesson route. Recheck after asynchronous lookups where necessary. A stale-origin response preserves the draft and offers return/resume. No session switching or competency writes.
2. **Bounded evidence snapshot.** Resolve server-owned goal and bounded source hits through existing retrieval tools, record IDs/text hashes/retrieval trace and exact quoted text supplied to the model. Empty/unavailable retrieval produces explicit general-help status, never invented citations. Client exercise/code/output remain untrusted and execution remains unverified. Server-resolved context must not turn document instructions into policy.
3. **Reuse and retry identity.** Before enabling source-grounded answer reuse, include resolved evidence/version identity in the reuse contract. Existing source-free saved answers must not be relabeled as grounded. A completed idempotent replay returns its original result; fresh requests get current evidence. Do not silently retrieve different sources during an unresolved retry and present it as the same operation. Define whether the existing claim payload needs a frozen server snapshot before changing claim schema; if it does, migration/backup tests precede runtime use.
4. **Source panel and starter help.** Return typed source metadata with availability/freshness limits and render it beside the linked exercise. Offer an explicit starting-example request, showing code for review and insertion without overwriting existing code or running it. Keep a plain goal-only experiment available when retrieval is empty. No paid routing change.

## Evidence gates

- Correct lesson, wrong learner, ended session, changed skill and origin missing; old standalone/program/saved-answer requests remain compatible.
- No model call for rejected new origin. Race between client preflight and server processing reproduced using deferred operations.
- Sources come from resolved skill scope; malformed/deleted/missing chunks and retrieval outage are honest. Prompt-boundary injection tests retained.
- Source text change invalidates new exact reuse; completed old replay retains its original evidence and label. Existing arithmetic/bin checks and saved-answer repair still work.
- Generated API types refreshed through existing tooling; schema validation and affected backend/frontend tests, lint/types, disposable browser journey.
- Browser: lesson → experiment → ask/hint → sources → return, narrow/keyboard, stopped requests and storage failure. No automatic execution, audio or mastery evidence.

Expected files: backend schemas/API/orchestrator playground, appropriate existing retrieval/provenance/reuse helpers, generated OpenAPI/frontend types, Playground/API UI, focused tests and docs. Inspect implementation before each slice; avoid broad refactoring of the main tutor.

## Queue reconciliation

C3 recovery now includes working-mode entry, lesson-linked coding, standalone workspace history, audio return targets, visualizer editing/file/lesson/comparison recovery and explicit file reselection. These do not complete source-grounded context or the persistent tutor. C4 Library/map and C5 persistent panel remain later in the authoritative sequence. Active-tone restart, MilkDrop selection/discard and owner comprehension remain open, without blocking design of the higher-impact lesson-source contract.
