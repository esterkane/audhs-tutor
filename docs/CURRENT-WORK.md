# Current work and next acceptance gates

Reconciled 2026-10-03 against current code, slice records and two independent queue reviews. This page is the current navigation point; older dated handoff entries remain historical evidence. A shipped slice does not close its entire stage. Both repository variants remain private.

## Working baseline

The app has editable learning areas, explicit lesson activation, guided project study, notebook starter/return flow, local browser execution plus a separate local scientific notebook environment, saved-answer search and feedback, and local speech services. Voice uses local speech recognition and synthesis. General tutoring keeps existing local routing; the previously approved answer-feedback route remains a narrow hosted exception. Recent local-model comparisons do not justify promoting either tested local candidate for general answer feedback.

Recent verified changes include explicit local bin-boundary checks, an optional group-count calculator, answer drafts bound to tutor focus, recoverable feedback reads/writes, and atomic notebook/dataset loading with retry. See the corresponding slice documents. Audio ownership for readings, voice, listening clips, ambient sound, output tests and visualizer monitoring is integrated; physical headphone audibility remains unverified.

Acquisition, stored source text, search indexing, activated lessons and executable notebooks are separate states. Private coverage reconciliation found empty and malformed notebooks plus duplicate-path evidence; recovered text is not a repaired executable notebook. Full external-resource and course coverage remains incomplete. Detailed acquisition reports and scripts belong only in the private archive.

## Prioritized next work

1. **R3 content-version and unresolved-request recovery.** Bind assessment/review submissions to the content the learner actually saw. Preserve completed original results; do not silently grade changed content or repeat an unconfirmed model call. Implement and test one path at a time.
2. **Integrated daily learning acceptance.** Choose topic → explanation → notebook practice → feedback → stop/resume, with source failure, storage denial, keyboard and narrow/zoom variants. Record owner comprehension and physical audio separately from automated tests.
3. **Material coverage.** Resume account-backed collection after sign-in; use the private ledger for bounded recovery and verify storage/index targets before claiming availability. Never simulate attendance or submit assessments.
4. **C01a/M00 source metadata.** Reconcile version/rights evidence with current source and backup models, then add the planned registry/check records. Manual explicit update checks precede any scheduling; local hash equality does not establish upstream currency.
5. **Visual learning V00/V01.** Record the typed visual architecture decision and harden the benchmark before model evaluation/rendering. The audio visualizer is separate.
6. Continue dependent authoring/resource and optional code-tutor/avatar tracks under their existing plans, rather than starting parallel replacement architectures.

## Stage ledger

| Track | Current state | Remaining acceptance |
|---|---|---|
| R0/R11 | Partial | Current evidence ledger and integrated release matrix; latest-head CI, security and cross-browser coverage |
| R1 | Core implemented | Integrated selection, existing-session choice and review recovery record |
| R2 | Partial | Remaining service/worker/stream/voice failure matrix |
| R3 | Partial | Content revisions, legacy callers and unresolved pre-commit recovery |
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

## Next execution prompt: R3 content versions

Read AGENTS, architecture, data/event rules, `audhs-state-reliability`, and the R3 stage before editing. Inspect `orchestrator/assessment_requests.py`, `kernel/review_requests.py`, `db/workspace_requests.py`, schemas, frontend submission hooks and existing recovery tests. First reproduce a submission after its question or rubric changes while the learner still sees an earlier version.

Define the exact content snapshot/fingerprint and its owner. Completed request replay must return the immutable original outcome without regrading; new submissions with stale or unknown version evidence need explicit compatibility handling. Do not add the current mutable content hash blindly to an idempotency payload, which could reject legitimate completed retries. Preserve unsent answers, source context and recovery state. A claim with no committed outcome is uncertain, not permission to repeat inference automatically.

Implement one bounded assessment path before extending reviews. Test edited prompt, rubric and expected answer; same-key replay after content changes; new stale submissions; concurrent requests; legacy versionless callers; lost response after commit; and unconfirmed work. Use disposable data/fake providers, then independent code/pedagogy review. A schema or migration decision must include backward compatibility and backup recovery. Keep routing, live curriculum and mastery history unchanged outside the explicitly tested submission behavior.

## Evidence boundaries

Automated tests do not certify owner comprehension, Bluetooth output, VoiceOver behavior, universal model correctness or rights to distribute material. Own-voice benchmark recordings remain required by the accepted gate. Optional source discovery/scheduling is not enabled by this status page. Original reports, private data and acquisition tooling remain excluded from the sanitized variant.
