# Current work and next acceptance gates

Reconciled 2026-10-03 against current code, slice records and two independent queue reviews. This page is the current navigation point; older dated handoff entries remain historical evidence. A shipped slice does not close its entire stage. Both repository variants remain private.

## Working baseline

The app has editable learning areas, explicit lesson activation, guided project study, notebook starter/return flow, local browser execution plus a separate local scientific notebook environment, saved-answer search and feedback, and local speech services. Voice uses local speech recognition and synthesis. General tutoring keeps existing local routing; the previously approved answer-feedback route remains a narrow hosted exception. Recent local-model comparisons do not justify promoting either tested local candidate for general answer feedback.

Recent verified changes include explicit local bin-boundary checks, an optional group-count calculator, answer drafts bound to tutor focus, recoverable feedback reads/writes, and atomic notebook/dataset loading with retry. See the corresponding slice documents. Audio ownership for readings, voice, listening clips, ambient sound, output tests and visualizer monitoring is integrated; physical headphone audibility remains unverified.

Acquisition, stored source text, search indexing, activated lessons and executable notebooks are separate states. Private coverage reconciliation found empty and malformed notebooks plus duplicate-path evidence; recovered text is not a repaired executable notebook. Full external-resource and course coverage remains incomplete. Detailed acquisition reports and scripts belong only in the private archive.

## Current owner scope — UX read recovery (2026-10-04)

Implemented [Preferences read recovery](slices/preferences-read-recovery.md): initial failure Retry/Home, cached-data refresh warning, bounded shared reads, and cancellation of stale reads before saving. Five browser and eighteen unit checks pass; lint/types/build pass with known warnings. No learning logic changed. Map read recovery is now verified (two browser/two unit checks, lint/types/build); see slices/map-read-recovery.md. C0 route/context inventory is complete in ux/CONTEXT-INVENTORY.md (23 browser/7 unit checks). Bounded C1 grouped navigation is implemented (slices/grouped-navigation.md):25 browser/four unit checks and lint/types/build pass. Park/menu obstruction is corrected by normal-flow header capture (slices/parking-header.md); Preferences200% reflow remains open. C2a area/draft URL history is implemented with dirty-editor protection (slices/area-location.md). C2b tab-local browsing context foundation is implemented (slices/browse-area-context.md). Next adopt the authoritative uploaded design tokens/components in bounded slices; broader shell adoption and owner acceptance remain open. Other routes, settings semantics, complete layout adoption and human acceptance remain open.

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
| R5 | Largely unstarted | Question suspension/replacement in selectors and review queues; answer replacement is different |
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
