# R3: prepared assessment recovery contract

Status: proposed next implementation; no recovery policy change accepted or shipped by this document.

## Current evidence
The new `test_assessment_crash_recovery.py` exits real child processes after durable `prepared` and `inference_started` transitions. Parent lookup remains unresolved; same-identity submission returns409; the claim/phase survives with zero attempts, competency evidence, model calls or saved tutor answers. These tests exercise durable repository primitives and real process death, not a real provider or the entire grading pipeline. Both cases plus existing request/execution tests pass:21 total. Ruff passes. Log: /tmp/assessment-crash-boundaries.log.

## Problem and boundary
Prepared work may be abandoned before inference, but the database phase alone cannot prove its worker is dead. Deleting old claims based on age, a timeout, process IDs alone or missing output risks duplicate inference. A caught cancellation is also not equivalent to a dead process: cancellation can interrupt cleanup, and scope-based cancellation may prevent further awaits. Preserve current conservative behavior until ownership is implemented and tested.

Only a verified abandoned **prepared** execution is a candidate for explicit recovery. `inference_started`, legacy missing execution, unknown schema, missing/replaced lock evidence and distributed/unsupported database ownership remain uncertain. `grade_ready` continues through the existing no-inference finish path; completed outcomes replay unchanged.

## Implementation sequence
1. Record the ownership decision against ADR-0018's same-host primitive before structural work. Do not directly couple assessment services to an ingest-named module or silently generalize its current public contract.
2. Acquire ownership before the claim becomes recoverable and retain it through gateway/result/learning boundaries. Persist versioned ownership identity bound to claim generation. Define a migration and backup/restore behavior: restored metadata without original lock evidence must remain unknown.
3. Add read-only classification that attempts the original verified lock, rechecks claim generation/phase/response under a short transaction, and never treats age as proof. Never hold a database write lock during inference.
4. Add an explicit continuation action, not automatic regrading at startup. Revalidate learner/session, original answer, content fingerprint and current eligibility. Specify behavior for ended sessions and process-rotated content tokens before coding; preserve old answers rather than treating stale tokens as permission to submit changed work.
5. Concurrent continuation and original completion must serialize. Never delete a replacement claim, replace a saved grade, or erase separately committed accounting. A failure after a new gateway entry must again remain uncertain unless a grade was durably saved.

## Acceptance gates
- Live worker with arbitrarily old timestamp cannot be reclaimed; actual dead prepared worker can be offered recovery only with valid ownership evidence.
- Two explicit continuations, late original completion, missing/replaced locks, canonical path aliases, restore without locks, migration from current DB and unknown/legacy rows.
- Failure before/after gateway entry, grade persistence and learning commit; interrupted inference is not automatically repeated.
- Original request/content identity, learner/session isolation, changed/deleted questions, ended sessions and preserved accounting.
- UI keeps original answer, clearly names the safe action, and still allows stop/change topic. Keyboard/narrow/slow/error journeys and independent code/pedagogy review.

This is a bounded pre-inference recovery plan. It does not recover a provider result that was never persisted or establish exactly-once remote execution. Cancellation cleanup is a separate audit, not a shortcut around these ownership gates.


2026-10-05 compatibility/design follow-up: see assessment-ownership-design.md for nullable metadata, stable payload identity, preserved import adapter, restored-ownership limits and explicit continuation contract.21 existing compatibility tests pass; implementation remains pending.
