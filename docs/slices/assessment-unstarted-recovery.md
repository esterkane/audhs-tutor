# Recovery of provably unstarted assessment requests

A newly claimed assessment submission may release its claim after an ordinary exception only when its own execution has not entered the model gateway or attempted the learning-state commit, and rollback succeeds. This covers deterministic preparation/write failures and prompt preparation failures before model entry. An explicit resend retains the original answer and identity.

The per-submission guard is irreversible during normal execution: gateway entry is marked before awaiting it, and learning commit is marked before awaiting commit. Gateway errors cannot prove no inference occurred. A commit error cannot prove no learning evidence was persisted. Those paths remain unresolved or recover their completed response; model accounting is unchanged. Cancellation, process death and previously unresolved claims are never automatically reclaimed.

Cleanup matches the exact newly inserted claim ID, learner, session, request key and absent response (SQL or JSON null). Delayed cleanup cannot remove a replacement generation or a completed result. Cleanup failure preserves the original error and requires lookup; elapsed time never permits takeover. No database migration or backup format change is involved. Model work remains outside the learning transaction.

## Verification

Focused assessment/content-version suite: 22 passed. Tests cover pre-model failure and original-identity retry, deterministic write rollback, gateway failure with no second call, lost learning-commit acknowledgement with one persisted attempt/evidence, cleanup failure, cancellation, old unresolved claims, replacement-generation protection and content changes during inference. Independent code review found no blockers or majors; corrected misleading pre-model content-error wording.

Full backend: 769 passed. Two isolated desktop/narrow recovery journeys passed; lint and strict types passed. Independent pedagogy review found no major learner-facing issues. No frontend runtime or schema changes.

## Remaining limits

A process crash after claiming but before model entry still leaves an uncertain request. Results computed by a model but not persisted cannot yet be recovered without new inference. A durable execution/outcome design is needed for those cases; this slice does not close R3 or promise exactly-once model execution.
