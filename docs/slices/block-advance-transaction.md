# Atomic next-activity transition

Failure injection proved that starting the next block could fail after the previous block's end/checkpoint had committed. Now the transition holds the same SQLite writer lock as Finish, refreshes ended-session state, stages end/start and commits once. Errors/cancellation roll back. Same from_index retries remain no-ops after success; grasp checks and content selection are unchanged. Standalone start/end commit defaults remain intact. No migration, UI, inference or scheduling rule change.

## Evidence

- Original failure test failed before the fix with persisted checkpoint/event drift.
- 44 affected backend tests passed before the three additional review cases. Eight focused cases now cover failure before/after next start, commit failure, cancellation, lost commit acknowledgement, stale ended-session identity, duplicate independent workers and advance/finish races. All eight focused cases pass (1.89 seconds).
- 18 real-sandbox browser pause/Back/Forward, delayed response and recap recovery cases pass at narrow/desktop widths with keyboard assertions. Existing pause screenshots inspected; UI unchanged.
- Full lint/type checks pass. Code review found no blocker/major and requested the added failure cases; pedagogy review found no blocker/major.

## Limits and next task

Only competing advance/finish workers are covered. Direct start/extend/replan writers need separate lifecycle validation. Postcommit response loss remains uncertain until state recovery or the explicit same-from_index replay; no automatic resend is introduced.

The lock predicates on the existing session owner; it does not authenticate the caller. Review found inherited raw session-ID lookups in block endpoints. Follow-up delivered: caller-ownership validation for block read/start/end/next/extend/replan, tested for no foreign writes; see plan-session-ownership.md. No broader security certification follows from transaction tests.
