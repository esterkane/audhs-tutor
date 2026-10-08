# Assessment outcomes after inference starts

Status: read-only local-worker status implemented locally; browser acceptance passed; publication pending. No retry or learning policy changed.

## Reconciled evidence (2026-10-08)
Prepared recovery is already implemented in `assessment-prepared-continuation.md`. Do not implement the older proposed prepared-recovery plan again. `orchestrator/assessment_requests.py::lookup` distinguishes completed, grade_ready, prepared_ready and unresolved. `grader.py` saves a validated grade before applying learning writes. `ModelCall` records usage/status and metadata; it is not a durable validated assessment grade and cannot substitute for one.

The remaining gap is a process/provider interruption after inference begins but before a validated grade is persisted. An elapsed timeout, successful usage row or absence of an attempt cannot prove that inference never happened. Repeated polling cannot recover output that was never saved. Current unresolved UI correctly blocks a new attempt, but cannot distinguish live work from a terminal unknown outcome.

## Next bounded implementation proposal
First distinguish provably ended execution from active/unknown execution using the existing ownership guard, without unsealing it or granting continuation. Preserve legacy/restored/missing proof as unknown. Add a read-only terminal status only when exact ownership evidence and durable execution phase agree. UI should explain that no saved result is available, retain/copy the original answer, and allow stopping/changing topic without promising that checking again will recover lost output. No automatic inference or learning writes.

Before changing code, reconcile `assessment_guard.py` seal semantics and filesystem replacement protection, then reproduce process-exit cases. Do not infer dead ownership from database phase alone. A sealed guard must remain ineligible for prepared continuation.

A separate future proposal may add explicit re-grading after confirmed terminal ownership. It needs a supersession/late-result contract, visible explanation of additional model work, original-answer retention, accounting and atomic evidence uniqueness. Do not silently add that behavior as a retry button. Saving intermediate provider outputs also needs bounded retention, learner scope, validation, export/wipe and privacy rules; it cannot eliminate the provider-to-durable-storage failure window.

## Acceptance for the read-only slice
- Live held lock, ended sealed lock, absent/replaced lock, legacy/restored state and changed content remain distinct where evidence permits.
- Same-identity submissions and continuation remain blocked after inference starts; zero extra model calls, grades, FSRS or competency writes.
- Concurrent completion wins over stale status; completed and grade-ready recovery retain existing behavior.
- Original answer survives reload, stop and topic changes; keyboard/narrow status flow is usable.
- Test actual child-process exit and persisted evidence; review code and learner-facing wording before publication.

This document does not close R3, establish exactly-once inference, or claim provider output can always be recovered.


## Implementation evidence
Added exact sealed-marker observation to AssessmentGuard, retaining the lock while re-reading durable request/phase/receipt. Lookup reports local_worker_stopped only for matching inference_started evidence; missing/legacy/held/restored-prepared evidence remains unresolved without that claim. Completed and grade-ready outcomes take precedence on the re-read. The flag proves only local ownership ended, not provider completion, and never authorizes continuation.

Recovery copy retains the original answer and names stop/change-topic without offering re-grading. Browser testing exposed loss of keyboard focus when Check saved result became disabled; it now remains focusable with aria-disabled and suppresses repeated activation while busy. Existing hook-level operation identity remains the concurrency guard.

49 backend tests pass, including real child exits, exact/malformed/held seals, prepared continuation and receipt replay.26 UI tests pass. Ruff, mypy217, focused ESLint, types and production build pass (existing bundle-size warning). Independent backend/copy review clear; six desktop/narrow keyboard browser journeys pass; narrow recovery screenshot visually inspected. No real learner submission or model call used for validation. Logs: /tmp/audhs-stopped-{backend-final,ui,browser,build,mypy}.log.
