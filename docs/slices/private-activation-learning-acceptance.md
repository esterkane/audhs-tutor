# Private activation learning acceptance

A saved answer can become a reviewed private lesson draft, then an explicitly activated lesson available for selection. This slice corrects the obsolete Ask disclosure saying activation is unavailable. It changes no learning logic, events, grading, scheduling, modes, energy behavior or controls.

## Evidence
- Real HTTP/storage integration: activation receipt IDs match catalog, direct selection, started/resumed session, learning object and available assessment. Session can end. No assessment attempts, task reviews, memory or model calls are created by these steps. Eight activation API tests pass.
- Combined Ask draft/recovery and activation/recovery browser journeys: four pass at390/1280, keyboard, reload, Back, axe and overflow checks. Transport fixtures are synthetic; these do not prove a full real browser-to-database authoring journey.
- Initial combined run failed two stale tests expecting the removed shared activation button. Updated them to assert the incomplete private draft's actionable validation and absent activation control, retaining unexpected-write checks.
- Visual inspection found obsolete Ask copy. New copy directs the learner to saved-draft review and private activation; accuracy and source-rights caveats remain.
- Targeted ESLint, TypeScript and backend Ruff pass. Prior runtime backend suite is reused; only one API test and one copy sentence changed.

## Remaining
Full browser authoring-to-study flow against real HTTP/storage, actual answer submission for this new origin, and human comprehension remain unverified. This is not proof of factual correctness or independently demonstrated learning. No live learner content was activated or changed.

## Reviews
Bounded test code review and wording pedagogy review report no blockers or majors. No application logic changed.
