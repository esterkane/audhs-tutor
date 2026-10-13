# Reversible Ask diagram archive controls

Archive/Restore now use the existing versioned command API. They preserve all content
versions, reviews and provenance and trigger no inference or learning-state writes.
New actions read current state/revision; a changed archive state requires refresh
instead of silently inverting an action the learner did not see. Pending commands
freeze document/revision/direction under one key. Answer-scoped retry remains reachable
when a successful archive with a lost response removes the document from the list.

A confirmed operation refreshes the document library; its receipt is never treated
as authoritative current state. Confirmation names the affected diagram and offers
explicit navigation to archived/active views. Read errors remain separately visible.
Stop waiting does not claim to undo a saved action. New reviews are locked during
archive uncertainty; existing review receipt recovery remains available. Unmount
aborts waiting and guards late component updates. No automatic deletion or expiry.

Verification: 662 frontend tests, full lint/types and production build pass; 12 sandbox
browser journeys pass, plus the two archive journeys rerun after confirmation-label
refinement. Desktop/390px archive → lost response → reload → same-key recovery →
restore → active presentation works without additional generation. Archive keyboard
activation, no horizontal overflow and both screenshots inspected. Existing journeys
retain source text, review retries, failure fallbacks and accessibility scans.
Bounded code/provenance review found no blockers or majors. Backend unchanged from
1557 passing tests; command transaction/ownership/archive semantics were not changed.
Existing ResizeObserver warnings and the build chunk warning remain.

Next: structured immutable version editing, stale-revision comparison/recovery and
semantic-quality work. The prior manual native keyboard-select/screen-reader gate
remains open. This completes archive controls, not the entire visual lifecycle.
