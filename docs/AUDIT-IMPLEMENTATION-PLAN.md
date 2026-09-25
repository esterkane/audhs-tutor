# AuDHS Tutor — audit implementation plan

Prepared 2026-09-25 from the supplied UX/UI/technical audit. Planning and skill creation only; no application fixes, dependency installs, live-data migrations, publication, commits or pushes are performed by this package.

## Main decision
Keep the existing architecture. First make the chosen lesson, review queue, saves and recovery trustworthy. Then simplify the daily learning path. Add richer representations only after these foundations are reliable. Editable cross-course areas remain the primary organizing model.

## Baseline and evidence
Audit and current HEAD: `5c21e190b4867e7f2102c1cb080af6053b494368`. The working tree contains later uncommitted visualizer and area-selection work; preserve it. Current source spot checks confirm F01/F02/F08/F10/F11/F12/F13 code patterns; F04 remains a persistence risk supported by multiple commits, not a reproduced corruption incident. No fresh application test suites were run for this planning task. All other findings require current-code reconciliation before implementation.

Important delta: `@xyflow/react` and `wavesurfer.js` already exist in the current package manifest for visualizer work. Do not propose installing a second graph/audio stack. `@codemirror/language`, React Hook Form and Dexie are not direct dependencies in the inspected manifest. Existing visualizer V0–V3 are recorded as implemented; V4 portable-contract acceptance and native work remain separate pending scope. The Udemy batch remains partially blocked; this plan does not mark it complete.

## Execution contract
Use `R0–R11` IDs to avoid confusion with the historic P0–P9 programme or roadmap stages. Each stage may be split into bounded vertical slices; finish and review each slice before starting its dependent work. Follow existing feature-slice, migration, event and pedagogy conventions; owner-only `/adr`, `/commit`, `/handoff`, `/build-stage` invocation policy remains unchanged. Update shared handoff directly with exact evidence and remaining work.

Use disposable database/sandbox for tests and publication journeys. Preserve inherited changes. Local execution and fake providers first; a configured OpenAI key does not authorize hosted runs or routing changes. Keep optional confidence, unconditional stopping, explicit adaptations, source provenance and server-owned learner state. No automatic training from question feedback.

Required verification follows the repository feature-slice contract: failing reproduction before a defect fix; backend/frontend suites and lint; generated API types after schema changes; migration/backup checks for schema changes; targeted browser journeys. Record code review and pedagogy review for learning-flow/prompt/grader changes. Do not report historical suites as newly run.

## Implementation stages and copyable prompts

### R0 — Reconcile the baseline and reproduce defects
Depends on: none. Audit coverage: all findings baseline. Status: **planned**.

**Work:** Read the audit, current HEAD, dirty diff, handoff and accepted ADRs. Inventory current routes, tests and dependencies. Reproduce F01/F02 with failing integration tests before fixes; record other defect evidence without calling it reproduced. Keep newer visualizer work intact.

**Acceptance gate:** A dated evidence ledger distinguishes audit-only, current-code-confirmed, reproduced, fixed-and-tested and deferred. Record exact commands and revision; historical test totals are not fresh results.

**Implementation prompt:**
```text
Implement R0 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R1 — Honor selected lessons and stable review queues
Depends on: R0. Audit coverage: F01 F02 F13. Status: **planned**.

**Work:** Use a typed area/course/skill navigation intent and validate eligibility server-side. Carry the explicit skill through Home to session creation. Resolve an existing session explicitly without silently mutating its block. Replace mutable-array review indexing with item identity, reviewed IDs and a recoverable queue; Together uses the active block/topic.

**Acceptance gate:** A non-default lesson is shown and stored in the server checkpoint with and without an existing session. Rate A in [A,B], fetch [B] via Show all, and still display B. Test refetch, remount, cap changes, no duplicate ratings, and Together return route.

**Implementation prompt:**
```text
Implement R1 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R2 — Make failures, streams, workers and voice recoverable
Depends on: R0. Audit coverage: F03 F06 F07 F10 F11 F12 F14 T02. Status: **planned**.

**Work:** Add consistent typed API errors, query cancellation, read timeouts and loading/error/empty/success views; retain usable content. Guard stream callbacks AND finalization with request identity. Register worker error listener and settle on dispose. Send voice text only on OPEN and preserve unsent input. Lock parking-lot saves and retain text on failure. Implement clear-model-override with capability filtering.

**Acceptance gate:** Exercise 404/500/offline, stale session, delayed old stream finalization, worker crash/dispose, WebSocket CONNECTING stop, disconnected Send, repeated parking-lot Enter, and reset-route persistence after reload. A failed source request must not assert deletion. No blind mutation retries.

**Implementation prompt:**
```text
Implement R2 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R3 — Persist learning evidence atomically and idempotently
Depends on: R1. Audit coverage: F04. Status: **planned**.

**Work:** Define client submission IDs and learner-scoped uniqueness for attempts and review ratings. Bind IDs to an immutable payload digest; conflicting reuse returns a conflict. Grade outside long database transactions, then persist attempt/evidence/FSRS/competency changes atomically under one transaction owner. Handle concurrent duplicate requests; separate model-call accounting and crash recovery from learning-state commits.

**Acceptance gate:** Lost response then retry returns the original result with exactly one attempt, evidence contribution and FSRS update. Inject failure between each write and verify rollback. Race two equal keys and reject equal key/different payload. Test migration, backup/export and learner scoping.

**Implementation prompt:**
```text
Implement R3 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R4 — Recover drafts and reconcile session transitions
Depends on: R1 R2 R3. Audit coverage: F09 F15 T03 U06. Status: **planned**.

**Work:** Specify a versioned draft envelope keyed by learner/session/activity/content version, with saved timestamp, partial/completed status and conflict handling. Prefer existing backend drafts for durable work; compare browser storage only for recovery needs. Preserve prompt, delivered explanation, answer and selected view. Define Pause, Finish and Change topic semantics; server-confirm transitions while keeping local drafts. Propose retention/purge policy before destructive cleanup.

**Acceptance gate:** Refresh, route away/back, reopen tab, failed save, quota/storage denial, content revision and stale checkpoint all have explicit recovery. Pause restores the same work; Finish records only completed work; changing topic handles the old session. Stopping requires no confidence answer or recap.

**Implementation prompt:**
```text
Implement R4 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R5 — Suspend and replace incorrect questions with history intact
Depends on: R3 R4. Audit coverage: F05 U08. Status: **planned**.

**Work:** Add active/suspended/superseded/retired lifecycle and typed correction inbox. Reporting records feedback; suspension is an explicit learner action. Cover all selectors and review schedulers. Preview publication additions/replacements/affected reviews; preserve old attempts and evidence. Version-check edits and make publication transactional and repeat-safe.

**Acceptance gate:** Suspend a question, verify it cannot be newly selected or reviewed, retain historical attempts, correct it and preview/publish only in sandbox. Test already queued items, concurrent edits/publications, same-version retry, and explicit restore policy. Feedback alone changes neither mastery nor model weights.

**Implementation prompt:**
```text
Implement R5 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R6 — Build structured content editing and complete source inspection
Depends on: R4 R5. Audit coverage: F08 U07 U13 T05. Status: **planned**.

**Work:** Expose server-authoritative typed draft schemas, field-level errors and conflict tokens. Edit goal, example, question, answers, rubric, prerequisites and source passages; advanced JSON remains optional. Store citation/source-version associations with cached representations and show sources for hints/alternatives. Add source-first browsing and import preflight with permitted paths, formats and required services. Split large routes as behavior is moved, not via a rewrite.

**Acceptance gate:** Fresh/cache-hit representations expose identical provenance; missing versions disclose gaps. Invalid edits are rejected with field errors, two-editor conflicts preserve both work copies, route changes retain drafts. Preflight differentiates local path access from browser upload and never implies arbitrary filesystem permission.

**Implementation prompt:**
```text
Implement R6 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R7 — Simplify the daily learning journey and accessible shell
Depends on: R1 R2 R4 R6. Audit coverage: U01 U02 U03 U04 U05 U14 U16 A01 A02 A03 A04 A05. Status: **planned**.

**Work:** Prototype Learn/Practice/Progress/Settings navigation with Resume first and one target chooser. Keep cross-course areas editable and courses as provenance. Deliver stable topic/step/saved status and one primary action per phase; help, sources, park and stop remain reachable. Provide no-active-lesson and low-capacity paths. Group preferences, serialize per-key writes, make recap a restart point. Add route titles, h1, focus/skip navigation, form/status primitives, readable Markdown, radio semantics and responsive layout.

**Acceptance gate:** Walk through returning learner, empty area, only-a-few-minutes, save-for-later, failure and recap paths. Verify keyboard-only operation, editor escape, screen-reader smoke, 320px reflow, 200% text, 400% zoom, long content and dark/system/reduced-motion settings. Owner comprehension is a separately recorded gate, never inferred from screenshots or axe.

**Implementation prompt:**
```text
Implement R7 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R8 — Explain progress and evaluate tutoring quality
Depends on: R3 R5 R6. Audit coverage: U09 T06 T07 T08. Status: **planned**.

**Work:** Build task-specific fixture suites for relevance, correctness, grounding, no-source behavior, hint leakage, malformed output and programming execution evidence. Version quality evidence by model/task/prompt/dataset. Show evidence dimensions, diversity, last assessed, prerequisites and recommendation reasons, with unassessed distinct from incorrect. Evaluate retrieval coverage and area-source inclusion/omission. Do not change mastery weights or provider routing based on provider brand.

**Acceptance gate:** Held-out programming cases compare explanations to executed results. Check repeated-question inflation, delayed-transfer evidence, stale source versions, empty retrieval and unsupported claims. Show task-level pass/fail with sample size and limitations. Local-first remains default; hosted comparisons require explicit budgeted scope; no broad quality certification from historical 3/5 results.

**Implementation prompt:**
```text
Implement R8 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R9 — Improve coding, diagrams and measured frontend performance
Depends on: R2 R6 R7. Audit coverage: U10 U11 U12 T01. Status: **planned**.

**Work:** Lazy-load heavy routes with Suspense/error boundaries and measure initial Home work. Reuse existing CodeMirror; add direct language dependency only through the project decision convention. Add named code experiments, copy/download, snapshot-bound tutor context and narrow Code/Output/Help views. Improve searchable/filterable map with list fallback. Prototype deterministic numeric widgets and validated diagram schemas with source links; preserve newer visualizer behavior.

**Acceptance gate:** Record build gzip and real browser transfer/interaction before/after using identical conditions. Treat 200kB gzip as provisional, not proof of speed. Test worker-backed execution and context snapshot, numeric widget invariants, text/table equivalents, reduced motion and lazy-load failure. Practice never awards mastery.

**Implementation prompt:**
```text
Implement R9 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R10 — Make local jobs, voice and diagnostics operationally clear
Depends on: R2 R4 R8. Audit coverage: T04 T10 U15 U17. Status: **planned**.

**Work:** Extend durable SQLite run/item records to area drafting and model jobs, with restart reconciliation and bounded retry. Correlate action/request/retrieval/model/event identifiers in local diagnostics with minimal content logging. Expose local service health and supported voice languages. Use a shared audio controller and supported playback controls. Simplify experiments around question, evidence and uncertainty.

**Acceptance gate:** Restart mid-job without losing completed work or duplicating drafts. Simulate Ollama/Qdrant/TTS/Pyodide failure and give actionable recovery. Test overlapping audio, interrupt/reconnect and text fallback. Owner-recording voice gate stays open until genuinely met. Experiments retain uncertainty and do not claim clinical effects.

**Implementation prompt:**
```text
Implement R10 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

### R11 — Verify integrated accessibility and distribution boundaries
Depends on: R7 R8 R9 R10. Audit coverage: A06 T09. Status: **planned**.

**Work:** Run the ten audit acceptance journeys end-to-end in isolated data, including Firefox/WebKit where available and explicit untested-platform notes. Keep local services loopback-only. Before any network distribution, review Host/Origin/WebSocket checks, ownership and ingestion roots. Evaluate hostile-code isolation separately from ordinary Pyodide execution; no sandbox-escape claim or broad distribution implied.

**Acceptance gate:** Publish a release evidence matrix with functional, persistence, accessibility, quality and performance results separated. Verify backup/recovery, no live learner changes in tests, no unexplained model routing changes, and all blocker/major findings resolved. Security expansion and native packaging remain separate approved work.

**Implementation prompt:**
```text
Implement R11 from docs/AUDIT-IMPLEMENTATION-PLAN.md in /Users/saru/projects/audhs-tutor. Read AGENTS.md, CLAUDE.md, the latest HANDOFF and this stage first. Use audhs-audit-slice plus the relevant reliability, content-correction or learning-ux skill. Reconcile current code; do not assume the audit is still exact. Deliver one bounded vertical slice of this stage, with the acceptance cases above, existing required reviews and exact test evidence. Preserve inherited changes. Record covered audit IDs, unfinished work and the next prompt in the shared handoff. Do not silently implement other stages, change model routes, publish live curriculum, or commit/push. If a design decision is required, prepare the concrete alternatives and continue unaffected work.
```

## Complete finding-to-stage ledger

Every finding is planned; none is marked fixed by creating this document. “Current code” is source inspection, not an end-to-end reproduction.

| ID | Finding | Stage | Evidence at planning time |
|---|---|---|---|
| F01 | “Learn this” loses the chosen skill | R1 | Current code checked; regression test still needed |
| F02 | “Show all” can skip due cards and claim completion | R1 | Current code checked; regression test still needed |
| F03 | Failed requests can look like endless loading or empty content | R2 | Audit evidence; reconcile in R0 |
| F04 | Assessment retry can duplicate or partially persist learning evidence | R3 | Current code; atomicity failure still needs reproduction |
| F05 | New content does not actually replace bad questions | R5 | Audit evidence; reconcile in R0 |
| F06 | Returning a model route to “profile default” does nothing | R2 | Audit evidence; reconcile in R0 |
| F07 | Some source failures are explained incorrectly | R2 | Audit evidence; reconcile in R0 |
| F08 | Cached alternate explanations lose returned provenance | R6 | Current code checked; regression test still needed |
| F09 | Optimistic phase changes are not reconciled with failed checkpoints | R4 | Audit evidence; reconcile in R0 |
| F10 | Old stream completion can overwrite a newer request's busy state | R2 | Current code checked; regression test still needed |
| F11 | Worker crashes are not wired to the intended run error handler | R2 | Current code checked; regression test still needed |
| F12 | Voice stop/fallback needs transport-state guards | R2 | Current code checked; regression test still needed |
| F13 | “Working alongside” can name the wrong lesson | R1 | Current code checked; regression test still needed |
| F14 | Parking a tangent has no pending/error treatment | R2 | Audit evidence; reconcile in R0 |
| F15 | Unsaved draft and session recovery is inconsistent | R4 | Audit evidence; reconcile in R0 |
| U01 | Make the primary navigation reflect learner tasks | R7 | Proposal; validate against current implementation |
| U02 | Put Resume or Start at the top of Home | R7 | Proposal; validate against current implementation |
| U03 | Use one learning-target chooser | R7 | Proposal; validate against current implementation |
| U04 | Keep administrative work out of low-capacity learning | R7 | Proposal; validate against current implementation |
| U05 | Make the session's primary action stable | R7 | Proposal; validate against current implementation |
| U06 | Treat Pause, Finish and Change topic as distinct intentions | R4 | Proposal; validate against current implementation |
| U07 | Replace JSON-only lesson editing with a structured editor | R6 | Proposal; validate against current implementation |
| U08 | Give feedback a useful correction outcome | R5 | Proposal; validate against current implementation |
| U09 | Explain progress through evidence | R8 | Proposal; validate against current implementation |
| U10 | Improve map navigation before installing a graph library | R9 | Proposal; validate against current implementation |
| U11 | Make “Show it differently” genuinely multimodal | R9 | Proposal; validate against current implementation |
| U12 | Build the playground around experiments with clear outcomes | R9 | Proposal; validate against current implementation |
| U13 | Improve source browsing as a learner tool | R6 | Proposal; validate against current implementation |
| U14 | Make preferences readable and stable while editing | R7 | Proposal; validate against current implementation |
| U15 | Make voice readiness understandable before playback | R10 | Proposal; validate against current implementation |
| U16 | Turn recap into a useful restart point | R7 | Proposal; validate against current implementation |
| U17 | Simplify experiments without overstating conclusions | R10 | Proposal; validate against current implementation |
| A01 | Add a consistent page and focus system | R7 | Proposal; validate against current implementation |
| A02 | Finish the design system | R7 | Proposal; validate against current implementation |
| A03 | Test reflow and readable controls | R7 | Proposal; validate against current implementation |
| A04 | Correct selection semantics where helpful | R7 | Proposal; validate against current implementation |
| A05 | Improve learning-content typography | R7 | Proposal; validate against current implementation |
| A06 | Expand accessibility verification beyond axe | R11 | Proposal; validate against current implementation |
| T01 | Reduce initial frontend work with existing React tools | R9 | Proposal; validate against current implementation |
| T02 | Make async state contracts consistent | R2 | Proposal; validate against current implementation |
| T03 | Consolidate drafts without creating a second learning kernel | R4 | Proposal; validate against current implementation |
| T04 | Persist long-running job status | R10 | Proposal; validate against current implementation |
| T05 | Strengthen typed domain boundaries | R6 | Proposal; validate against current implementation |
| T06 | Evaluate models by tutoring task | R8 | Proposal; validate against current implementation |
| T07 | Make mastery evidence robust before making it more persuasive | R8 | Proposal; validate against current implementation |
| T08 | Improve retrieval quality through measured coverage | R8 | Proposal; validate against current implementation |
| T09 | Keep runtime boundaries explicit | R11 | Proposal; validate against current implementation |
| T10 | Use the observability already collected | R10 | Proposal; validate against current implementation |

## Decisions and deliberate deferrals

- Existing architecture and local-first policy: retain. No new orchestration framework, database, cloud analytics or distributed job stack.
- Draft persistence: compare existing backend endpoints with browser recovery needs in R4. Propose retention and content-conflict policy before implementing purge. Do not install Dexie by default.
- Editor: propose direct @codemirror/language when R9 requires it; reconcile the existing four-package frontend rule through the owner ADR convention.
- Structured editor: start with typed server schema and existing form controls. React Hook Form is optional only if field-array/validation complexity justifies it.
- Graph: reuse the already installed React Flow only when interactive map requirements justify it; always retain a usable list.
- Idempotency, lifecycle and durable-job migrations: design uniqueness, learner scoping, transaction ownership, compatibility and recovery before changing schema.
- Pause/Finish semantics and retention: proposed here, not an accepted ADR. Work must preserve the existing stop-without-questions guarantee.
- Tauri, PWA, multi-user/network exposure and hostile-code execution are separate conditional projects. Do not turn this audit into their authorization.
- Voice personal-recording gate, visualizer V4 acceptance, and blocked Udemy resources remain independent open items.

## Acceptance journeys and release evidence

1. Resume exact topic and unfinished answer — R1/R4/R7. Evidence must name the test/manual procedure and actual result.
2. Empty area gives a useful next action — R7. Evidence must name the test/manual procedure and actual result.
3. Stop generation preserves delivered text — R2/R4. Evidence must name the test/manual procedure and actual result.
4. Show all preserves unreviewed cards — R1. Evidence must name the test/manual procedure and actual result.
5. Retry a lost submission without duplicate progress — R3. Evidence must name the test/manual procedure and actual result.
6. Suspend and replace an incorrect question with history — R5/R6. Evidence must name the test/manual procedure and actual result.
7. Keyboard start, answer, sources, stop and return — R7/R11. Evidence must name the test/manual procedure and actual result.
8. Narrow/zoomed long formula, title and code remain usable — R7/R9/R11. Evidence must name the test/manual procedure and actual result.
9. Model outage offers actionable recovery — R2/R10. Evidence must name the test/manual procedure and actual result.
10. Recommendation and progress explain supporting evidence — R8. Evidence must name the test/manual procedure and actual result.

Measure completion/recovery success and time to useful learning content under documented conditions; use source inspection and delayed transfer where measurable. Do not optimize streaks or time-on-app. Automated accessibility tests do not certify WCAG conformance; owner comprehension, assistive-technology checks and real-model/voice quality are separate gates.

## Implementation update — 2026-09-25

R1a/F02 implemented and code/pedagogy reviewed; 377 backend tests, 103 frontend tests and lint passed. See docs/slices/audit-review-queue.md. R1b/F01/F13 are now implemented and reviewed: 378 backend tests, 107 frontend tests and lint passed (docs/slices/audit-lesson-intent.md). R0 remains partial; R1 sandbox browser acceptance remains open. All other stages remain planned.

## Start here
Run R0, then R1. R2 can follow as a separate bounded reliability slice. R3 is required before lifecycle/publication changes. Do not postpone F12 merely because general voice polish belongs to R10. Do not postpone T06 until release: quality fixture design begins in R0, actual model evidence is gathered in R8 before recommending broad use.

## Skills and continuity
Four focused skills accompany this plan: `audhs-audit-slice`, `audhs-state-reliability`, `audhs-content-correction`, and `audhs-learning-ux`. They supplement existing project skills, not replace them. Codex discovery copies live in ~/.codex/skills; Claude copies live in .claude/skills. Keep matching copies synchronized when revising them. The repository plan is authoritative; output copy is the delivery snapshot.
