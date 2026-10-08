# Current work and next acceptance gates

## Current execution checklist — 2026-10-05

This checklist supersedes older “next” instructions below; those paragraphs are dated history, not parallel work orders. The broad goal remains active. Keep the original archive private and the sanitized repository public (owner update2026-10-05) and preserve the independent acquisition worktree delta.

Recently delivered: authoritative palette/components, local Inter and Roboto Mono, original logo/favicon, grouped desktop/narrow shell, persistent companion context, contextual capture/return and reminder Undo, tab-local recent contexts, keyboard quick navigation, search for areas/project guides/saved explanations/source passages. Skill search and result-group keyboard jump links are published in both private variants. These capabilities do not close whole-stage human or accessibility acceptance.

Execution order:
0. **Owner latency priority:** streaming, local model residency, explicit session preparation and unindexed-history lookup avoidance are shipped. The live backend was refreshed. Current synthetic explicit TutorTurn samples reached first text in6.44/2.06/2.04s and completed in13.05/7.64/8.74s; these are sequential warm-cache observations, not an end-to-end guarantee. See slices/local-tutor-latency.md for evidence and rejected experiments. Context-size reduction, prompt reordering and empty-preparation cache invalidation have already been investigated; do not repeat them without new evidence. Output-limit safeguards cover local streamed replies and buffered plain text; structured termination remains separate. Preserve model quality/context. Verify current CI from GitHub rather than treating an older passing run as newest-head evidence.
1. Completed: skill-search paired publication and result-group jump links. Exact lesson-choice links do not auto-start/change a session.
2. Search usability: review long combined results on narrow screens, category orientation, independent failure/retry, return paths, and accessibility. Search still excludes notebook cells, edits, personal notes and saved thoughts; define indexing/privacy/version rules before adding them.
3. Integrated daily-learning acceptance (ux/DAILY-LEARNING-ACCEPTANCE.md): explicit Pause races, checked-feedback return/reload, post-feedback and post-reveal concept help, review-recovery focus across loading states, and two consecutive incorrect-answer controls now have bounded regression evidence. Do not redo those slices absent a regression. A header-link probe reproduces a late redirect only with an artificial suspended destination; current App routes have no Suspense boundary, so this is not established as a production defect and does not justify a navigation refactor. A real Chromium sandbox probe now confirms browser Back stays on Home after delayed start/movement-next/review-next responses (3 passed; desktop and narrow; checkpoint and single transition preserved). Temporary probe and log are retained in /tmp/navigation-pending-probe.spec.ts and /tmp/navigation-pending-probe.log; this is bounded investigation evidence, not a committed regression suite. A second real Chromium probe passed six header/Forward cases, including keyboard activation of Home and narrow navigation; no late redirect or duplicate transition was observed (/tmp/navigation-header-forward.spec.ts and /tmp/navigation-header-forward.log). Remaining: complete keyboard/zoom/preference journeys, and human comprehension/physical audio. Fix reproduced S3/S4 issues one at a time; automated checks do not close human gates.
4. Reliability follow-ups: uncertain post-inference outcomes, remaining content/draft recovery, question suspension/replacement, job restart recovery. New owned local imports now reconcile safely after hard exits and explicitly resume remaining work; see slices/ingest-restart-recovery-plan.md and ADR-0018. Legacy unknown ownership, persistent job IDs and other job types remain open. Owned prepared assessments now offer explicit original-answer continuation after same-host guard, phase, request and content verification (slices/assessment-prepared-continuation.md). The live backend migration is activated. Stale curriculum save/activate/discard conflicts are now guarded by reviewed revisions (slices/draft-version-conflicts.md); tab-local unsaved editor reload recovery is implemented (slices/draft-editor-reload.md). Broader R4 and cross-surface recovery remain open. R5 learner-scoped eligibility/receipt foundation is implemented (slices/question-state-foundation.md); review queue/direct-rating integration is implemented (slices/question-review-eligibility.md), assessment submission/recovery guards are also implemented (slices/question-assessment-eligibility.md). Assessment selectors/canonical generation and exercise/listening guards are implemented (slices/question-selection-eligibility.md). Ordinary lesson exclusion/restore controls and paginated Preferences discovery are implemented and live (slices/question-practice-controls.md), with desktop/narrow keyboard journeys. Remaining R5: other surface controls, correction inbox and reviewed replacement/publication; human acceptance remains open. Reuse existing durable outcomes; never infer safe resend from timeout alone.
5. Continue remaining design adoption per affected screen; retain reading size, local fonts, control visibility and honest evidence semantics. Browser zoom/screen-reader/full preference-flow coverage remain open.
6. Resume material/provenance/quality work and dependent visual-learning/authoring/resource/code-tutor/avatar/native queues using their existing contracts. Acquired text is not proof of complete material coverage or a runnable notebook.

See slices/recent-contexts.md for current search evidence; design/BRAND-FOUNDATION.md for colors, typography, logo and limitations. The stage ledger below remains a broader backlog. Estimates communicated to the owner are planning ranges, not completion promises.


Reconciled 2026-10-03 against current code, slice records and two independent queue reviews. This page is the current navigation point; older dated handoff entries remain historical evidence. A shipped slice does not close its entire stage. The sanitized variant is public again by owner decision2026-10-05; the original archive remains private.

## Working baseline

The app has editable learning areas, explicit lesson activation, guided project study, notebook starter/return flow, local browser execution plus a separate local scientific notebook environment, saved-answer search and feedback, and local speech services. Voice uses local speech recognition and synthesis. General tutoring keeps existing local routing; the previously approved answer-feedback route remains a narrow hosted exception. Recent local-model comparisons do not justify promoting either tested local candidate for general answer feedback.

Recent verified changes include explicit local bin-boundary checks, an optional group-count calculator, answer drafts bound to tutor focus, recoverable feedback reads/writes, and atomic notebook/dataset loading with retry. See the corresponding slice documents. Audio ownership for readings, voice, listening clips, ambient sound, output tests and visualizer monitoring is integrated; physical headphone audibility remains unverified.

Acquisition, stored source text, search indexing, activated lessons and executable notebooks are separate states. Private coverage reconciliation found empty and malformed notebooks plus duplicate-path evidence; recovered text is not a repaired executable notebook. Full external-resource and course coverage remains incomplete. Detailed acquisition reports and scripts belong only in the private archive.

## Current owner scope — UX read recovery (2026-10-04)

Implemented [Preferences read recovery](slices/preferences-read-recovery.md): initial failure Retry/Home, cached-data refresh warning, bounded shared reads, and cancellation of stale reads before saving. Five browser and eighteen unit checks pass; lint/types/build pass with known warnings. No learning logic changed. Map read recovery is now verified (two browser/two unit checks, lint/types/build); see slices/map-read-recovery.md. C0 route/context inventory is complete in ux/CONTEXT-INVENTORY.md (23 browser/7 unit checks). Bounded C1 grouped navigation is implemented (slices/grouped-navigation.md):25 browser/four unit checks and lint/types/build pass. Park/menu obstruction is corrected by normal-flow header capture (slices/parking-header.md); Preferences200% root-text reflow is verified at320/640/1280 with keyboard saving; actual browser zoom remains open (ux/DAILY-LEARNING-ACCEPTANCE.md). C2a area/draft URL history is implemented with dirty-editor protection (slices/area-location.md). C2b tab-local browsing context foundation is implemented (slices/browse-area-context.md). Next adopt the authoritative uploaded design tokens/components in bounded slices; broader shell adoption and owner acceptance remain open. Other routes, settings semantics, complete layout adoption and human acceptance remain open.

## Prioritized next work

1. **R3 unresolved-request recovery.** Assessment/challenge/listening/code submissions and review/vocabulary ratings now bind to displayed content, preserve original completed outcomes and offer explicit refresh without losing earlier work (see the assessment/review content-version slices). New model-free review ratings now roll back their claim and learning writes together, enabling safe original-identity resend (see `docs/slices/review-atomic-recovery.md`). Caught pre-model/pre-commit assessment failures now release only their own claim after rollback (see `docs/slices/assessment-unstarted-recovery.md`). Validated grades now persist before learning writes and can be finished explicitly without inference; crash-orphaned claims and model results lost before persistence remain uncertain.
2. **Integrated daily learning acceptance.** Session-entry failure now offers bounded loading, Retry and Home while preserving mounted drafts on refresh failure (`docs/slices/session-loading-recovery.md`). Review loading is likewise bounded and preserves revealed cards during refresh failures (`docs/slices/review-loading-recovery.md`). Successful notebook checks now survive explanation edits/navigation (`docs/slices/notebook-checked-run-retention.md`). Choose topic → explanation → notebook practice → feedback → stop/resume, with source failure, storage denial, keyboard and narrow/zoom variants. Record owner comprehension and physical audio separately from automated tests.
3. **Material coverage.** Authenticated collection resumed: three additional text sections are stored and five exact index points verified (2026-10-04). Five additional linked source files are now stored at fixed revisions; 28 canonical index points were verified, including two pre-existing deduplicated chunks. A further 50 linked downloads yielded 173 imported documents; all 180 canonical index points were checked. A follow-up JSON-record loader recovered two datasets (five more verified points); 65 media entries and five SVG assets remain outside this text/code pass. See `docs/slices/json-record-datasets.md`. A repository recovery pass added 352 documents with all 200 associated canonical index points verified; three oversized archives and skipped media/unsupported formats remain open. The read-only private ledger now reconciles separate recovery directories without duplicating overlapping reports. Use the private ledger for bounded recovery; video, interactive and external-resource coverage remains incomplete. Never simulate attendance or submit assessments.
4. **C01a/M00 source metadata.** Reconcile version/rights evidence with current source and backup models, then add the planned registry/check records. Manual explicit update checks precede any scheduling; local hash equality does not establish upstream currency.
5. **Visual learning V00/V01.** Record the typed visual architecture decision and harden the benchmark before model evaluation/rendering. The audio visualizer is separate.
6. Continue dependent authoring/resource and optional code-tutor/avatar tracks under their existing plans, rather than starting parallel replacement architectures.

## Stage ledger

| Track | Current state | Remaining acceptance |
|---|---|---|
| R0/R11 | Partial | Current evidence ledger and integrated release matrix; latest-head CI, security and cross-browser coverage |
| R1 | Core implemented | Integrated selection, existing-session choice and review recovery record |
| R2 | Partial | Remaining service/worker/stream/voice failure matrix |
| R3 | Partial | Assessment/review versions and atomic review recovery implemented; caught pre-model failures recover; crash/inference outcome recovery remains |
| R4 | Partial | Consistent draft/content conflict handling across surfaces |
| R5 | Partial | Suspension/reuse guards and main activity controls implemented; reviewed replacement and integrated acceptance remain |
| R6 | Partial | Structured curriculum editing and conflict preservation |
| R7/Q5 | Partial | Complete keyboard/zoom/screen-reader/comfort matrix and owner comprehension |
| R8/Q2/Q7 | Partial | Held-out semantic correctness, source support and delayed transfer; diagnostics are not learning-outcome proof |
| R9 | Partial | Integrated coding/map accessibility and measured frontend performance |
| R10/Q6 | Partial | Durable job restart recovery, action-specific readiness and evidence-based progress |
| Q0 | Implemented | Conversation target, mode, draft and continuation slice verified |
| Q1 | Partial | Fresh/stopped/notebook/unavailable-source journey and first-useful-action baseline |
| Q3 | Partial | Integrated report → correction → reviewed replacement across answers and graded items |
| Q4 | Enhancements unstarted | Optional timeline/capture shortcut with correct focus; timer/parking foundations already exist |
| QA answer library | Partial | Broader source/reuse acceptance, main-lesson replay and scoped portability/backfill |
| V visual learning | Assessed, implementation queued | V00 decision → V01 benchmark hardening → V02 local quality; not the audio visualizer |
| A authoring | Planned | A00 reconciliation after V04, provenance/versioned editing/export gates |
| E curated resources | Planned | E00 provider/privacy contract after V04; acquisition scripts are not resource-card UX |
| S codebase tutor | Assessed | S00 allowlisted corpus decision → immutable source snapshots and cited explanations |
| C/M documents | Assessment partial, implementation planned | C01a registry/check records and M00 rights/routing/export inventory; unknown evidence stays unknown |
| Avatar | Assessed, runtime absent | Optional synthetic prototype, playback-envelope adapter, sensory/privacy/licence gates |
| Native visualizer | Separate, unimplemented | Portable-format decision and native foundation/hardware gates |

## Next execution prompt: R3 unresolved requests

Read the assessment/review content-version slices and current durable claim/outcome implementation. Reproduce failures before inference, after inference but before learning writes, and after committed learning writes with lost delivery. Define which failures are provably safe to retry and which must remain uncertain. Do not infer absence of work from a missing outcome or elapsed time. Preserve completed legacy replay, learner scope, immutable request identity, original prompt/answer and separately logged model accounting. The bounded atomic review-rating path is implemented; extend the analysis to inference paths without holding a database write lock during model calls. The bounded grade-ready recovery implementation is in `docs/slices/assessment-durable-result-plan.md`; inference without a persisted result remains unresolved. Any claim-state schema change needs an explicit migration/backup compatibility plan, disposable upgrade tests and independent reviews. Keep routes, content publication and existing learning history unchanged.

## Evidence boundaries

Automated tests do not certify owner comprehension, Bluetooth output, VoiceOver behavior, universal model correctness or rights to distribute material. Own-voice benchmark recordings remain required by the accepted gate. Optional source discovery/scheduling is not enabled by this status page. Original reports, private data and acquisition tooling remain excluded from the sanitized variant.

## Proposed runtime extensions

The owner-proposed memory, voice and development-tool additions are reconciled in [runtime-extension-evaluation](runtime-extension-evaluation.md). Evaluation and daily-learning acceptance come first; Hindsight/local memory comparison and optional hosted voice experiments follow. No new provider is activated and no architecture replacement is accepted by this queue entry.

## Design adoption checkpoint

Existing palette roles and focus styling now follow the uploaded canonical tokens; see design-palette-adoption in docs/slices. Typography, primitives and the authoritative navigation/workspace composition remain open. The additional workspace document is authoritative, recorded in docs/design/source/README.md.

## Context shell design progress

Shared palette/buttons/panels now follow uploaded specifications. Desktop rail is implemented; mobile navigation now uses a closed-by-default disclosure with focus recovery (slices/mobile-navigation.md). These are partial C1/C2 visual stages. Next reconcile compact header and contextual mode/tool entry; persistent tutor, complete mobile composition, font system and human acceptance remain outstanding.

## Contextual tools checkpoint

Lesson-linked coding experiments now retain isolated drafts and validate the current origin (slices/lesson-experiment.md). Audio-lab detours now return to their named coding workspace (slices/visualizer-return-context.md). C3 remains partial: source-grounded context, project/review entry and route-independent paused visualizer state remain; C5 persistent tutor is not implemented.

## C3 next implementation: server-verified lesson origin

Tool recovery slices are recorded in visualizer-*-recovery and related slice docs. The next substantive gap is lesson-grounded coding help: read slices/lesson-playground-evidence-plan.md. Begin with optional typed origin/server validation, preserving existing standalone/program callers and completed replays. Source snapshots/reuse require their own bounded follow-up. Full C3/C4/C5 remain open.


## C3 work-alongside recovery — 2026-10-04

The embedded quiet-panel choice survives matching-session/tab detours and reload without audio autoplay. See slices/alongside-recovery.md for verification and limits. Source retrieval/starter scaffolding shipped separately; older TODOs are historical. Remaining project/review/audio entry contracts and C5 stay open.


## C3 task notebook re-entry — 2026-10-04

Task notebook view restores for matching course/section and starter/dataset paths; explicit return clears it. Results remain temporary; no code autoruns. See slices/task-notebook-view-recovery.md for evidence and versioning limits. Full C3/C5 remains open.


## C3 project location links — 2026-10-04

Project course/step/notebook view have URL identity and browser-history recovery; existing notes remain scoped. See slices/project-location-links.md. Relevant authored lab links remain next; full C3/C5 is open.


## C3 authored audio-lab links — 2026-10-04

Optional project-to-audio lesson relations now have validation, explicit explanation selection and named return. See slices/project-audio-lab-contract.md for synthetic browser/review evidence. No real material mapped yet; relevance requires source inspection. Full C3/C5 remains open.


## Current execution boundary — 2026-10-04

C3 contextual tool capabilities and recovery have shipped in the corresponding slice records. No relevant audio-lab relationship was found in the current authored project sections; do not add arbitrary lab links. This is a source-coverage limit, not a reason to invent unrelated C3 tasks. Human C3 acceptance remains open. Next bounded implementation is the C4 area-scoped map contract in [area-map-plan](slices/area-map-plan.md). Stored skill-area membership exists, but the current map API does not expose scoped results. Preserve all learning decisions while adding the read-only projection. Earlier “next C2/C3” paragraphs above are historical.


## C4 area map implemented — 2026-10-04

Map now offers explicit area URL scope and a global choice, using stored membership and transitive prerequisites. Outside-area prerequisites are labeled and readable as text. Learning goals/mastery/unlocks remain unchanged. See slices/area-map.md for backend/browser/build/review evidence and the native-select automation limitation. Next C4 work: organize existing Library/source discovery; persistent tutor remains C5. No broad phase closure or human-comprehension pass claimed.


## C4 Library source discovery — 2026-10-04

Library now offers Sources alongside Saved answers, reusing read-only retrieval and the source viewer with URL/history/focus recovery.15 component checks and6 browser journeys pass; final visual/lint/types/build evidence and limits are in slices/library-sources.md. Learning logic and model routing unchanged. C4 bounded implementation is present; human acceptance remains open. Next C5: inspect and define persistent tutor target/draft/stream lifecycle before changing the shell.


## C5 companion context foundation — 2026-10-04

Captured material, unapplied edits and one previous capture now survive route changes/reload; applying material explicitly separates conversation identities. Existing close/request/media cleanup remains intact. See slices/companion-context.md and persistent-tutor-contract.md for baseline, tests, reviews and limits. Next: implement desktop panel/narrow sheet using this state owner; footer placement is still temporary. Full C5 and human acceptance remain open.

2026-10-08: Review cards now offer explicit question exclusion/restoration, preserving notes and requiring queue refresh before rating. API19/UI20, desktop/narrow keyboard journeys, lint/types/build and bounded review passed. No scoring/scheduling changes. See docs/slices/review-question-controls.md. Dedicated activity controls and correction/replacement remain open.

2026-10-08: Code exercise loading failures now offer Retry/exclusion management, preserving cached code and focus. Parent/child remount retry loop fixed. Focused17 component tests, desktop/narrow browser, lint/types/build and bounded review verified. See docs/slices/code-exercise-read-recovery.md. Dedicated activity exclusion controls remain next.

2026-10-08: Primary code-question exclusion/restoration preserves editing/local Run and requires fresh checks before renewed grading. Hint exposure is retained. Focused11 tests, two keyboard/narrow browser journeys, lint/types/build and bounded review passed. See docs/slices/code-question-practice-controls.md. Linked explain-back/challenge/listening controls remain open.

2026-10-08: Challenge exclusion/restoration preserves answers through explicit refresh and same-question re-entry.8 focused tests, two desktop/narrow keyboard browser journeys, lint/types/build and bounded review pass. Generation entry was fixtured: cached challenge start still eagerly requires retrieval/embedding. See docs/slices/challenge-question-controls.md for evidence and next fix. Linked explain-back/listening controls remain open.

2026-10-08: Saved/excluded challenges now resolve before retrieval initialization.21 focused backend tests and two real-start desktop/narrow journeys pass; Ruff/mypy and bounded review clear. See docs/slices/challenge-cached-start.md. Generation misses still require configured services; linked explain-back/listening controls remain open.

2026-10-08: Listening exclusion/restoration preserves answers and playback state, with safe MCQ reselection after changed content.13 focused tests, three browser journeys, lint/types/build and bounded review recorded in docs/slices/listening-question-controls.md. Physical audio remains separate; linked code explain-back and correction/replacement remain open.

2026-10-08: Linked code explain-back exclusion/restoration now preserves code, run results and typed answers; explicit refresh updates only linked question fields.12 focused tests and four desktop/narrow browser journeys pass, lint/types/build and bounded review clear. See docs/slices/code-explain-practice-controls.md. R5 reviewed correction/replacement and integrated acceptance remain open.

2026-10-08: Replacement investigation identified shared-assessment versus learner-scoped eligibility and fixed linked-question references as architectural boundaries. Added docs/slices/question-replacement-plan.md with five ordered slices and acceptance contracts. No runtime change or replacement implementation claimed. Next: bounded learner-owned read-only correction inbox; lineage schema requires ADR before publication work.

2026-10-08: Read-only reported-question inbox is available in Preferences with learner-owned pagination, original wording, changed/unavailable status and retry preserving loaded reports.16 backend/5 frontend tests and two keyboard desktop/narrow journeys pass; lint/types/build and bounded review clear. See docs/slices/question-correction-inbox.md. Resolution/editing/publication remain unimplemented.

2026-10-08: Prepared proposed ADR-0019 for learner-owned correction storage, durable draft identity, repeat-safe commands and future-only replacement resolution. Code inspection confirmed process-bound public tokens and loose AssessmentIn payload validation; explicit typed adapters and source-version checks are required. No runtime/schema change. Next: durable proposal foundation and tests; publication remains disabled.

2026-10-08: Internal correction drafts now persist original question/rubric snapshots and repeat-safe create/save/discard receipts (migration773f25ae3e92). Full backend982 passed plus a corrected table-inventory expectation; final17 database/draft/export/wipe/migration tests, Ruff/mypy and review clear. See docs/slices/correction-draft-foundation.md. No editor/API/publication; typed adapters and source-version checks are next.

2026-10-08: Internal correction review now validates core/challenge shapes and captures private source identities for new drafts; legacy/missing sources remain explicit.22 focused tests, Ruff/mypy213 and bounded review pass, including normalized-option ambiguity fix. See docs/slices/correction-validation-sources.md. No editor/API/publication yet; code execution and listening revalidation remain separate gates.

2026-10-08: Private correction-draft API now supports owned prepare/create/read/list/save/discard and receipt lookup.26 focused tests, Ruff/mypy214, generated frontend types/lint/build and bounded review pass. See docs/slices/correction-draft-api.md. No editor or publication; visible typed authoring and dirty-work recovery are next.

2026-10-08: Visible correction drafts now support explicit answer disclosure, structured editing and repeat-safe save recovery with newer local edits retained.16 focused tests, four desktop/narrow keyboard browser journeys, visual inspection, lint/types/build and bounded review pass. See docs/slices/correction-draft-editor.md. Publication and replacement resolution remain gated; original practice and learning evidence are unchanged.

2026-10-08: Correction drafts now show original/current and conflict saved/current changed-field comparisons.10 focused tests, two keyboard desktop/narrow browser journeys, visual checks, lint/types/build and bounded review pass. See docs/slices/correction-comparison.md. Ownership/resolver and publication-impact gates remain next; no learning logic changed.

2026-10-08: Replacement visibility inventory identified distinct access/eligibility predicates, shared-only canonical caches, review LEFT JOIN fallback and explicit ownership portability requirements. See docs/slices/replacement-visibility-matrix.md. No runtime/schema change; next implement and prove ownership across the matrix before lineage/publication.
