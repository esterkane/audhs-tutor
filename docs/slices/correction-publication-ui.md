# Explicit correction publication and recovery

Implemented 2026-10-08. The saved-draft impact preview now explains publication blockers and permits an explicit source/answer confirmation when supported. Publication applies only to this learner's future practice. It creates a new identity, preserves past answers/grades/schedules and has no one-click undo; exclusion or another correction remains available.

The editor disables publication for dirty/conflicting drafts, missing/changed sources, unsupported code/listening content, pending commands and failed preview refreshes. Confirmation resets on refresh/submission. The command hook persists the exact publication body/action ID before sending, validates the returned draft/revision/status/replacement identity, and supports receipt lookup or identical retry after a lost response/reload. Confirmed publication makes the retained draft read-only. Server revalidation remains authoritative.

## Evidence

- 22 backend impact/draft/publication tests passed; final19 publication tests include3 added missing-source/listening/code rejection cases (25 unique affected tests overall).
- 12 editor/impact component tests passed, including confirmation and lost publication response with reload.
- 4 real sandbox Chromium journeys passed at390/1280: existing edit/save recovery and reviewed publication with lost response/reload, single write, superseded original and retained read-only draft. Keyboard Enter/Space and horizontal reflow checked; both publication screenshots visually inspected.
- Ruff, strict mypy217, frontend lint/types/build passed; existing bundle-size warning remains.
- Independent code/pedagogy review clear. Live backup taken, backend restarted, schema c146f830ad92 and health verified. No real material was published.

## Remaining

Broader end-to-end report/queued-review/history and linked-exercise acceptance remains, as does human comprehension, assistive technology and explicit reversal policy. Code/listening publication is intentionally unavailable pending dedicated verification. Complete/unchanged source identity is not proof of answer correctness. No paid calls or learning-algorithm changes.
