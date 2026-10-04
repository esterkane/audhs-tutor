# Proposed next R3 slice: durable grade-result recovery

Status: design proposal, not implemented or an accepted schema change.

Persist a dedicated assessment execution record keyed to the exact request claim. Use versioned request/content identity and validated result, with phases prepared → inference_started → grade_ready → completed. Commit inference_started before gateway entry; persist a validated result before applying learning evidence. Do not hold a database write lock during model calls or erase independently committed model accounting.

Offer explicit “Finish saving this result” for grade_ready. Under a short write lock, verify ownership, claim generation, content identity and phase; write attempt, events, competency, FSRS, checkpoint, completed response and phase atomically. Concurrent finish calls return the original outcome without a model call. Changed/deleted content retains the result for inspection but prevents applying evidence. Define ended-session handling explicitly before implementation.

An inference_started record without a saved result remains uncertain. External provider return and SQLite persistence cannot be atomic; never infer safety from elapsed time. Legacy claims without execution records remain unresolved.

Before migration, reconcile backup privacy: avoid duplicating hidden keys or corpus passages into learner-only backups, or explicitly redact those fields and mark recovery unavailable after restore. Required acceptance: disposable old-schema upgrade and backup/restore, failure at each boundary, commit acknowledgement loss, concurrent finish, changed/deleted content, ended sessions, learner isolation, preserved accounting and no inference on replay. This proposal does not close R3.
