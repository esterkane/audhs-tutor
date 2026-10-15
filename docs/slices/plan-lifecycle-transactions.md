# Standalone plan writes versus Finish

Reproduced five failures: stale start/end/extend/replan requests were not rejected after Finish, and failed proposal generation left an energy change committed. The four API writes now share Finish's SQLite writer lock, refresh session state and reject completed sessions with `session_ended` (409). Their writes commit together or roll back on error/cancellation. Replan's energy, adaptation proposal and proposal event belong to that transaction.

Block/grasp rules, timer arithmetic, explicit energy and optional adaptation acceptance remain unchanged. Existing kernel helper commit defaults are preserved. No schema, model, UI or scheduling changes. The old start-after-end test expected generic 400; it now asserts the explicit 409 contract and unchanged block events.

## Evidence

- 30 focused lifecycle tests cover stale workers, both Finish ordering outcomes for all four actions, rollback after staged writes/cancellation, final commit failures, independent duplicate start/end, additive concurrent extensions, lost commit acknowledgement and unchanged-plan energy saving.
- 73 affected backend tests pass, including ownership, ordinary transitions, adaptation, atomic advance and finish.
- Full lint/type checks pass. Code and pedagogy reviews found no blockers/majors; additional reviewer-requested cases above pass.
- 18 isolated browser journeys pass (pause/resume, Back/Forward, delayed response and recap recovery) with keyboard and 390/1280px coverage. Desktop/narrow resumed screenshots inspected; no UI code changed. Initial run stopped on occupied sandbox port; alternate run was stopped before acceptance and final run used dedicated ports and `plan-lifecycle-check.db`. No learner database used.

## Limits / next step

This boundary covers the four API mutations, not every kernel caller. Checkpoint writes and adaptation acceptance/undo remain separate follow-ups. Lost commit acknowledgement is still uncertain; extension is additive and must not be automatically resent. Tests verify persisted state, not human comprehension or teaching quality.
