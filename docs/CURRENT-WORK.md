> Design authority update2026-10-11: follow [Complete design alignment](design/COMPLETE-DESIGN-ALIGNMENT.md). The new owner-supplied PDF consolidates the target; older conflicting prototype/rejection notes are historical. Implementation is partial design adoption; use the current reconciliation below before older next-step notes.

# Current work and next acceptance gates

## Actionable checkpoint — 2026-10-12

This checkpoint supersedes older stage TODOs below. Do not schedule completed
features again or use isolated UI checks to mark the complete design adopted.

**Delivered and verified in bounded flows:** content-first Learn and explicit help,
Pause/Focus/session options, area-based Explore without implicit session switching,
persistent companion, saved assessment links, correction publication/recovery,
local fonts/palette/logo, shared controls, CSV preview recovery, and Progress retry
focus. Actual200% Chromium checks now cover lesson/Preferences/Pause/reload,
Explore/selection and Search/return at light320/dark640 CSS pixels. Search targets
and initial/paginated Progress retry have separate keyboard/responsive evidence.
See HANDOFF.md and ux/ADVERSARIAL-USABILITY-REPORT.md for exact tests and limits.

**Outstanding work, in execution order:**

1. **Integrated acceptance:** latest-head CI must finish; prior passing heads are
   not proof for the newest commit. Continue the remaining daily-learning matrix
   against existing implementations, prioritizing reproduced blocked tasks or lost
   work over more isolated cosmetic changes. Do not repeat the delivered zoom cases.
2. **Human/assistive-technology acceptance:** owner re-entry, explanation clarity,
   screen-reader behavior and physical headphone/microphone output are still
   unverified. Automated fixtures cannot close these gates.
3. **Progress design semantics delivered:** explicit task/rubric reviews, frozen
   pre-inference eligibility and dated task-specific labels are implemented. Model
   checks/help and historical exclusions are disclosed; independence stays unverified.
   Real HTTP/storage and browser persistence acceptance passes. See
   slices/progress-reviewed-labels.md. Human interpretation remains unverified;
   grading and scheduling are unchanged.
4. **R3/R4 reliability:** persisted grade-ready continuation exists; outcomes lost
   after inference starts remain uncertain. Do not automatically resend. Remaining
   cross-surface draft/content recovery follows the existing contracts.
5. **Source/material quality:** private coverage ledger still has media, interactive,
   external-link and executable-notebook gaps. Stored/indexed text is not complete
   coverage or degree engagement. Preserve the separate acquisition worktree delta.
6. **Dependent queues:** M00 technical inventory is recorded in
   slices/material-rights-inventory.md; C01a/M01 metadata/rights design and M02
   enforcement remain open. Visual technology research, the standalone prototype
   and bounded schema/binding foundations are delivered; authored lifecycle and
   lesson integration remain open. Dependent A/E authoring/resources and optional
   S/avatar/native tracks remain as recorded in the stage ledger. No replacement architecture or
   hosted provider is authorized merely by this checklist.

Both repositories are PRIVATE, including the sanitized future-public variant.
Sanitation and separate histories remain required. Batch related work and validation;
reuse unchanged evidence and avoid commits solely to report CI polling.


## Current design reconciliation — 2026-10-11

Do not schedule already delivered design slices again. Bounded implementation now includes:

- Content-first Learn, three tutoring actions, in-place alternative explanations, one composer, responsive context and explicit Focus exit.
- Assessment revision with retained original feedback; repeated attempts do not duplicate competency/FSRS evidence. Grounded feedback help reads the saved assessment context.
- Learner Explore at `/explore`, distinct from preparation at `/areas`; Home browsing uses Explore and does not silently change the saved session.
- Progress links to owned saved assessment feedback, without inventing independent-application evidence.
- Shared saved-answer disclosures, enlarged-text reflow, whole-label mobile navigation with measured bottom spacing.
- Quick review rejects late redirects after navigation or Back. Server-side creation already started may still finish; browsing does not cancel learning records.

Evidence and remaining per-screen gaps: [complete design alignment](design/COMPLETE-DESIGN-ALIGNMENT.md).
Integrated local browser regression verification passed347 tests with20 intentional
opt-in skips before the latest bounded slices. Actual200% Chromium lesson checks now
cover light320/dark640 CSS pixels, sequential keyboard navigation, drafts and return.
Latest-head hosted CI, other-flow zoom, assistive technology and human re-entry remain
open. Initial lesson-entry/composer hierarchy is now implemented in a bounded slice;
see design/LESSON-ORIENTATION-CONTRACT.md for evidence and human acceptance. Do not
reimplement completed heading/Focus/navigation/reading-order changes. Both remotes remain private.
See the reconciled execution order in design/COMPLETE-DESIGN-ALIGNMENT.md. Broader
semantic quality, material coverage and dependent queues below remain active.

## Verified status reconciliation — 2026-10-08

Read this before older next-step notes. Persistent desktop tutor panel and narrow modal sheet are implemented (slices/companion-panel.md); skill search and category links also exist in routes/Search.tsx. Do not schedule their implementation again. R5 report inbox, correction editor, source/impact preview and explicit publication/recovery are implemented, with preserved-history integration evidence in slices/correction-publication-ui.md. Remaining R5: human acceptance, explicit reversal policy and independently verified code/listening correction support.

The next UX acceptance work is actual browser zoom/assistive-technology and human re-entry/comprehension. Search long-result keyboard/reflow acceptance now has a bounded 320/1280px, 200% root-text check; that is not browser zoom or proof of low cognitive effort. Notes/notebook indexing requires its privacy/version contract first. Existing latency and material-coverage gaps remain active. Earlier “persistent tutor not built” and “correction publication unavailable” statements are historical.

## Current execution checklist — 2026-10-05

This checklist supersedes older “next” instructions below; those paragraphs are dated history, not parallel work orders. The broad goal remains active. Keep BOTH repositories private (owner update2026-10-11), retaining the separate sanitized variant and preserve the independent acquisition worktree delta.

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


Reconciled 2026-10-03 against current code, slice records and two independent queue reviews. This page is the current navigation point; older dated handoff entries remain historical evidence. A shipped slice does not close its entire stage. Both variants are private by the latest owner instruction; the older public-visibility decision is superseded.

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
| R5 | Partial | Suspension/reuse guards and reviewed replacement/publication implemented; human acceptance, reversal policy and code/listening support remain |
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
| V visual learning | Research and standalone prototype delivered; integration partial | All13 candidates retained; interactive leakage experiment, local part help, bounded specs and persisted binding checks verified. Authored lifecycle, authenticated integration and semantic acceptance remain open; not the audio visualizer |
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

## Historical checkpoints — consult the actionable checkpoint above first

The following dated implementation notes preserve provenance. Their “next” and
“not implemented” statements are not current task assignments; later slice records
(including companion-panel and correction-publication-ui) supersede them.

## Design adoption checkpoint

Existing palette roles and focus styling now follow the uploaded canonical tokens; see design-palette-adoption in docs/slices. Typography, primitives and the authoritative navigation/workspace composition remain open. The additional workspace document is authoritative, recorded in docs/design/source/README.md.

## Context shell design progress

Shared palette/buttons/panels now follow uploaded specifications. Desktop rail is implemented; mobile navigation now uses a closed-by-default disclosure with focus recovery (slices/mobile-navigation.md). These are partial C1/C2 visual stages. Next reconcile compact header and contextual mode/tool entry; persistent tutor, complete mobile composition, font system and human acceptance remain outstanding.

## Contextual tools checkpoint

Lesson-linked coding experiments now retain isolated drafts and validate the current origin (slices/lesson-experiment.md). Audio-lab detours now return to their named coding workspace (slices/visualizer-return-context.md). C3 remains partial: source-grounded context, project/review entry and route-independent paused visualizer state remain; C5 persistent tutor is not implemented.

## C3 next implementation: server-verified lesson origin

Tool recovery slices are recorded in visualizer-*-recovery and related slice docs. The next substantive gap is lesson-grounded coding help: read slices/lesson-playground-evidence-plan.md. Begin with optional typed origin/server validation, preserving existing standalone/program callers and completed replays. Source snapshots/reuse require their own bounded follow-up. Full C3/C4/C5 remain open.


## C3 work-alongside recovery — 2026-10-04

The embedded quiet-panel choice now survives lesson/tool detours and reload within the matching session/tab, without audio autoplay.7 component tests and2 desktop/narrow browser journeys pass; visual, code and pedagogy review complete. See slices/alongside-recovery.md. Starter scaffolding/source retrieval shipped separately; older C3 source/starter TODOs above are historical. Next reconcile remaining project/review/audio context entry; full C3/C5 and owner acceptance remain open.


## C3 task notebook re-entry — 2026-10-04

Task notebook view now restores for matching course/section and starter/dataset paths; explicit return clears it. Notes and selected cell survive, results remain temporary and no code autoruns. See slices/task-notebook-view-recovery.md for tests, browser/review evidence and remaining source-version limits. Full C3/C5 remains incomplete.


## C3 project location links — 2026-10-04

Project course/step/notebook view now have URL identity and browser-history restoration; notes remain scoped to their existing stores. See slices/project-location-links.md. Next: explicitly authored relevant lab links using this return identity, not generic links for every lesson. Full C3/C5 remains open.


## C3 authored audio-lab links — 2026-10-04

Project sections can declare a validated audio lesson plus purpose. The lab verifies the relation and offers explicit explanation selection and named return, with no automatic sound or evidence.16 component checks and7 browser journeys pass; see slices/project-audio-lab-contract.md. No live material mapped yet. Inspect source relevance before enabling real links; full C3/C5 remains open.


## Current execution boundary — 2026-10-04

C3 contextual tool capabilities and recovery have shipped in the corresponding slice records. No relevant audio-lab relationship was found in the current authored project sections; do not add arbitrary lab links. This is a source-coverage limit, not a reason to invent unrelated C3 tasks. Human C3 acceptance remains open. Next bounded implementation is the C4 area-scoped map contract in [area-map-plan](slices/area-map-plan.md). Stored skill-area membership exists, but the current map API does not expose scoped results. Preserve all learning decisions while adding the read-only projection. Earlier “next C2/C3” paragraphs above are historical.


## C4 area map implemented — 2026-10-04

Map now offers explicit area URL scope and a global choice, using stored membership and transitive prerequisites. Outside-area prerequisites are labeled and readable as text. Learning goals/mastery/unlocks remain unchanged. See slices/area-map.md for backend/browser/build/review evidence and the native-select automation limitation. Next C4 work: organize existing Library/source discovery; persistent tutor remains C5. No broad phase closure or human-comprehension pass claimed.


## C4 Library source discovery — 2026-10-04

Library now offers Sources alongside Saved answers, reusing read-only retrieval and the source viewer with URL/history/focus recovery.15 component checks and6 browser journeys pass; final visual/lint/types/build evidence and limits are in slices/library-sources.md. Learning logic and model routing unchanged. C4 bounded implementation is present; human acceptance remains open. Next C5: inspect and define persistent tutor target/draft/stream lifecycle before changing the shell.


## C5 companion context foundation — 2026-10-04

Captured material, unapplied edits and one previous capture now survive route changes/reload; applying material explicitly separates conversation identities. Existing close/request/media cleanup remains intact. See slices/companion-context.md and persistent-tutor-contract.md for baseline, tests, reviews and limits. Next: implement desktop panel/narrow sheet using this state owner; footer placement is still temporary. Full C5 and human acceptance remain open.

2026-10-08: assessment-backed review cards now reuse explicit exclusion/restore controls with preserved notes and an explicit queue refresh; no rating evidence is inferred. See `docs/slices/review-question-controls.md`. Dedicated activity controls and correction/replacement remain open.

2026-10-08: Code exercise read failures now show Retry/exclusion management instead of disappearing; fixed parent/child retry loop and preserved cached code/focus. Focused17 component tests, desktop/narrow browser, lint/types/build and bounded review verified. See docs/slices/code-exercise-read-recovery.md. Dedicated activity exclusion controls remain next.

2026-10-08: Primary code assessments now support exclusion/restoration while preserving code and local Run. Restoration requires explicit refresh and rerun; hint exposure retained. Focused11 tests, desktop/narrow keyboard browser, lint/types/build and bounded review pass. See docs/slices/code-question-practice-controls.md. Linked explain-back/challenge/listening controls remain open.

2026-10-08: Challenge exclusion/restoration now preserves typed answers through explicit refresh and same-question re-entry. Fixed stale refresh after mode switch;8 focused tests and desktop/narrow browser controls verified. See docs/slices/challenge-question-controls.md. Next prerequisite: cached challenge start eagerly requires retrieval/embedding; browser generation entry was fixtured, not an offline-start pass. Linked explain-back/listening remain open.

2026-10-08: Saved/excluded challenges resolve before retrieval initialization; only generation misses need an embedder.21 backend tests and two real-start browser journeys pass, Ruff/mypy and bounded review clear. See docs/slices/challenge-cached-start.md; previous generation-entry fixture removed. Linked explain-back/listening controls remain next.

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

2026-10-08: Assessment ownership foundation implemented with migration924acd018f31, shared-only canonical caches, direct/review visibility gates and explicit private export/wipe.1006 backend tests, Ruff/mypy214, six keyboard desktop/narrow browser journeys, disposable migration and bounded review pass. Live schema upgraded/backend restarted. See docs/slices/assessment-visibility.md. Lineage, replacement resolution and publication remain next.

2026-10-08: Internal learner-owned question lineage and bounded future-practice resolver implemented;38 focused tests, Ruff/mypy215, backup/migration/export/wipe checks and bounded review pass. See docs/slices/question-replacement-lineage.md. Migration applied locally. No consumer integration or publication yet; connect future entry without redirecting history next.

2026-10-08: Code/linked-check and listening future entry now resolve owned replacements; canonical rows and old submission identities remain intact.42 backend tests, six desktop/narrow keyboard regression journeys, Ruff/mypy215 and review pass. See docs/slices/replacement-practice-entry.md. Selector chain consistency, explicit UI transition and publication remain open.

2026-10-08: Ordinary/challenge selection and optional recall now validate incoming replacement ancestry without changing ranked identity or history. Invalid optional recall cannot block Stop.33 backend tests, six desktop/narrow browser regressions, Ruff/mypy215 and review pass. See docs/slices/replacement-selector-validation.md. Explicit replacement UI and publication remain next.


2026-10-08: Read-only correction impact preview shows saved-revision review/exercise counts and current source excerpts, with dirty/stale/missing/truncated evidence explicit.19 backend,9 frontend and2 desktop/narrow keyboard journeys pass; visual inspection, lint/types/build and bounded review clear. See slices/correction-impact-preview.md. No publication or learning writes; atomic publish and explicit confirmation remain next.


2026-10-08: Internal correction publication transaction implemented with learner-owned identity, immutable receipts, exact-report resolution and unchanged learning history.37 backend tests, strict mypy217/Ruff, editor tests and2 desktop/narrow browser regressions pass; bounded review clear. See slices/correction-publication-transaction.md. No publish endpoint/UI or live publication; explicit confirmation/recovery and integrated acceptance remain next.


2026-10-08: Explicit correction publication now connects saved impact/source confirmation to the atomic service, with persisted same-command receipt recovery after lost response/reload.25 unique backend checks,12 UI tests and4 real desktop/narrow keyboard browser journeys pass; visual/lint/types/build and review clear. See slices/correction-publication-ui.md. Live schema c146f830ad92/health verified; no real publication. Broader report/history/linked-surface acceptance and reversal policy remain.


2026-10-08: Three real-API correction publication integration tests now verify report resolution, old-receipt replay, due-card exclusion, six learning tables retained and linked code-check redirection with persisted exercise unchanged. Final3 tests/Ruff pass; review findings fixed. See slices/correction-publication-ui.md. No runtime delta; human/reversal and unsupported-kind gates remain.


2026-10-08: Linux CI exposed inode reuse in import ownership recovery. New import locks/options carry an exact random v2 marker; legacy/missing/replaced proof remains unknown.60 ingest and32 targeted guard/recovery checks plus2 browser resume journeys pass; Ruff/mypy217/review clear. See slices/import-ownership-marker.md. Live backend updated; remote Linux rerun pending.

2026-10-08: Browser CI fixture isolation repaired: publication cleans only its synthetic question/source/dependencies in the sandbox, including committed lost-response replacements; delayed Home preference tests restore the prior mode. All12 ordered publication/Home/reading/exclusion/session journeys pass, focused ESLint and bounded review clear. Narrow publication screenshot inspected; keyboard and390/1280 reflow assertions retained. No application learning change. See slices/import-ownership-marker.md. Remote full CI remains to verify after push.

2026-10-08: Read-only assessment recovery distinguishes a released local grading worker with exact sealed proof from unknown/live ownership, without permitting repeat inference.49 backend,26 UI and6 desktop/narrow keyboard journeys pass; Ruff/mypy/types/lint/build and bounded review clear. Result-check focus is preserved while busy. See slices/assessment-unknown-outcome-plan.md; provider outcomes and explicit re-grading remain separate open work.

2026-10-11: Two external reference folders recovered privately;26 documents imported and52 canonical index entries verified. Four images and notebook execution remain open. Full CI eeba6b9 passed. See slices/material-subtree-recovery.md.

2026-10-11: Notebook status reads now time out visibly and offer explicit Retry; failed background polling stops.3 UI and3 desktop/narrow keyboard journeys, lint/types/build and review pass. Setup writes and learning logic unchanged. See slices/notebook-status-recovery.md.


2026-10-11: Owned revision retrieval and Try again/Next are implemented. Original
feedback remains available; deliberate revisions retain drafts across refresh and
use the existing submission/recovery owner. Cancel restores feedback/focus; source
version races return409. Final4 sandbox browser tests at390/1280,10 Session and6
revision-hook tests pass;18 final revision backend tests, types/lint and production
build pass. Desktop/narrow screenshots inspected; code/pedagogy reviews clear.
Existing large-chunk warning remains. Full Practice design, shared choice styling,
physical assistive-technology and human comprehension acceptance remain open.
See docs/design/PRACTICE-RETRY-CONTRACT.md.


2026-10-11: Assessment selections use semantic accent-tint plus the existing pressed
ring, leaving Check my answer as the filled primary action (PDF pp2/10). Other
Choice uses remain unchanged. Two real-API revision browser journeys pass at390
light/1280 dark, with keyboard/edit/reload/cancel/submission checks; screenshots
inspected.10 Session tests, lint/type/build and code/pedagogy reviews pass. Existing
large-chunk warning remains. Full secondary feedback-help controls and broader
Practice/Progress design acceptance remain open; grading is unchanged.


2026-10-11: Four post-feedback help actions now use owned immutable saved assessment
context, including options, submitted work and criteria. Dedicated escaped context
rejects oversized/incomplete records; contract identity separates saved assessments;
legacy retry payloads remain compatible. No grading changes.31 backend tests,17 UI
tests,2 keyboard/responsive browser journeys, types/lint/build and code/pedagogy reviews
pass. Narrow help screenshot inspected; existing build chunk warning remains. One
synthetic local gemma3:12b sample (11.1s total, no hosted call) correctly distinguished
the selected expression from the correct option; its recipe analogy was less direct
than ideal. This is limited sampling, not evidence of general teaching quality or
learning gains. Broader local-model evaluation, human/AT acceptance and remaining
Progress/Explore design alignment remain open. See ASSESSMENT-HELP-CONTEXT.md.


2026-10-11: Progress evidence now links to owned saved assessment feedback; unavailable
records are explicit. Read-only learner-scoped joins preserve pagination/counts.3
backend tests,4 final browser checks (Progress320/1280 plus assessment history),
types/lint/build and reviews pass. Keyboard link navigation opens saved feedback;
browser Back returns to the selected concept. Narrow full-page screenshot inspected.
Existing large-chunk warning remains. Historical help-selector test updated to the
new Explain the difficult part label. No competency or independence interpretation
changed. Broader human/AT and Progress evidence-level design acceptance remain open.


2026-10-11: Learner Explore now leads with areas and exact activated concepts, existing
descriptions/criteria, and explicit Home lesson selection. Preparation stays at/areas
with its existing edit guards; browse navigation/history are separate from learning.
Empty areas never substitute unrelated lessons. One backend membership/no-write test,
six navigation/browser checks plus final three Explore checks (including a real active
session preserved during selection), types/lint/build and reviews pass. Light320 and
dark1280 screenshots inspected. No learning-policy changes. Existing chunk warning
and broad human/AT acceptance remain; this does not complete the entire design system.
See docs/design/EXPLORE-LEARNER-CONTRACT.md.


2026-10-11: Global Browse area now uses the shared44px DisclosureSummary without
changing its native details owner/navigation.2 keyboard/responsive browser checks,
types/lint/build and code/pedagogy reviews pass; narrow open-state screenshot inspected.
5 preceding shell/header checks passed. Existing chunk warning remains. Screenshot
uses fixture area IDs without real concepts and honestly shows its loading-error
recovery; real concept/error flows were separately checked in the Explore slice.
Broader shared-control adoption and human/AT acceptance remain open.

2026-10-11 integrated design browser validation:347 passed,20 intentional opt-in skips.
Learn retry focus and narrow audio reflow corrected; see complete design alignment.
Actual browser zoom, human/AT acceptance and newest-head CI remain open.


2026-10-11: Actual Chromium 200% zoom now verified for lesson draft/context,
Preferences return, pause/resume and refresh at320/640 CSS pixels. Two browser
cases, focused lint/types and bounded reviews pass; compositor screenshots inspected.
No runtime/learning changes. Full-platform zoom, human/AT acceptance remain open;
DL-02 orientation density remains visible at narrow width. See
docs/ux/DAILY-LEARNING-ACCEPTANCE.md (Real Chromium browser zoom). Both repos private.


2026-10-11: DL-02 consolidated orientation is specified in
docs/design/LESSON-ORIENTATION-CONTRACT.md. Current duplication spans distinct
state owners; no speculative remount/refactor was made. Next prototype the
presentational composition against its draft/focus/mutation acceptance gates.
This contract is not implementation or a human-usability pass.


## Visual investigation completion boundary — 2026-10-12

The requested technology comparison, architecture recommendation and initial ML
prototype are delivered; keep all13 candidates in the specification for future
content creation. See research/visualization-technologies.md and
slices/visual-learning-prototype.md. The extra schema/database-binding foundations
are recorded in slices/visual-learning-binding.md. They are not a production
versioned-authoring feature or an accepted lifecycle ADR.

Storage audit: representation invalidation deletes rows; authored history must use
its own lifecycle. Learner backup retains derived artifacts under current policy;
export/wipe discovers learner-scoped tables through metadata. New tables still need
migration, ownership, immutable version/idempotency and nonempty backup/wipe tests.
Do not claim these future gates passed from the pure validators or prototype.

Return to the existing integrated UX/reliability acceptance queue before expanding
visual authoring speculatively. R3 grade-ready recovery is already implemented;
absence of a persisted inference result remains uncertain and must not auto-retry.
Latest full backend strict mypy passed227 source files. CI remains independently
pending behind active browser runs; prior-head success does not close latest-head CI.
