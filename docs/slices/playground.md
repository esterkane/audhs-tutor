# Coding playground and guided practice

A learner edits saved Python experiments, runs them locally and asks a tutor beside the workspace.
Start with a scratchpad or a worked → complete → independent pipeline exercise; each step keeps its own draft.
Tutor requests explicitly include bounded current code, last-run output and recent chat; stale output is labelled. No hidden edits or mastery claims.
Reuse CodeMirror, the pinned worker runtime, session ownership, model routing, asked/explained events and tutor/model traces. No new dependency or migration.
Mode/energy remain learner-controlled; practice has no timer or score. Native keyboard controls, editor escape and a stacked mobile tutor.
Visual workflow editing and real LangChain/n8n execution remain later stages; this slice includes only a conceptual pipeline map.

## Acceptance and verification

- Saved isolated scratch/worked/completion/independent workspaces: component and real-browser reload/switch tests.
- Real Python execution, stale-output indication, worker stop and runtime limits: browser journey plus component cancellation tests; existing offline runtime journeys still pass.
- Bounded explicit code/output/history context; code snapshots attached to chat and stale replies labelled. Failed requests retain questions; text typed while waiting is preserved.
- Session ownership/ended-session checks, escaped code/history boundaries, model/tutor traces and no assessment/competency writes: backend tests with fake providers.
- Accessibility: axe passed. Full lint, 342 backend and 57 frontend tests passed. All eight isolated browser journeys passed, including the new playground journey. Live UI inspected without submitting learning attempts.
- Code/pedagogy reviews cleared after fixing delayed-question clearing, stale reply context and a session-start race across workspace switches. Optional next-step control added for guided practice.

## Scope and remaining work

This is the first coding-playground/guided-practice slice: one scratchpad and one three-stage Python pipeline exercise. The conceptual pipeline map is not a visual workflow editor. Real LangChain/n8n execution, import/export and framework-specific lessons remain future work. Existing draft questions are not retired or activated by this feature.

Storage is per browser, not a server backup or cross-device workspace. Tutor chat uses the current learning session or an explicitly started session, without advancing planned blocks. Unsent chat questions and runtime output are temporary. Code suggestions are manual text; no automatic application.

Known quality limitation: local-model trials still contain an incorrect Python debugging explanation. Do not call tutor accuracy validated; see `evals/results/report-2026-09-24-playground.md`. The selected cheaper hosted candidate is documented in `docs/PROVIDER-COST-COMPARISON.md`; OpenAI provider integration and a quality evaluation are not included here.
