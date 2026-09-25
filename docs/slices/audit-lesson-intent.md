# Audit R1b — explicit lesson selection and active focus topic

Scope: F01 and F13. A map choice must reach session creation and the server checkpoint; an existing session remains unchanged until explicit replacement. Input: URL lesson ID. Output: selected lesson panel, keep-current or end/start action, server-owned skill and phase. Existing session events, modes, confidence and grading are unchanged. No new learning event or schema migration. Controls use existing keyboard-accessible primitives.

Map now navigates to /?lesson=<id> without changing Zustand skill/session identity. Home delegates that route intent to SelectedLesson; plain Home remains unchanged. Keep current restores server topic/phase. End-and-start preflights eligibility via GET /api/sessions/selection/{skill_id}, then ends the old session and creates one with explicit skill_id. POST revalidates eligibility. Selection remains in the URL on failure. If ending succeeded but starting fails, explicit copy says the old session ended and new lesson did not start. These two actions are not claimed atomic; full idempotency is R3.

Together reads active_skill rather than next_skill, returns via routeForPhase, and identifies itself as a quiet focus screen, not a human companion. API types regenerated with make gen-api.

## Verification

Map regression failed before implementation because selection silently navigated to /session. Integration tests now exercise actual Map → Home → explicit session POST for both no-session and existing-session cases. Further tests cover keeping the old review phase and rejecting a non-teachable unlocked choice before any end POST. Backend fixture verifies missing/locked IDs create no session and allowed choice persists in active_skill, state and checkpoint after GET. Together test distinguishes active from recommended skill and checks /review return.

Code and pedagogy review cleared majors after adding nonmutating eligibility preflight. Frontend 45 files / 107 tests and make lint passed. Backend final result in HANDOFF. No browser/owner-comprehension pass claimed; no fake model results presented as quality evidence.

## Boundaries

Preserved all inherited work and R1a review fixes. No new dependencies, paid API calls, live learner changes, commits or pushes. R1 source/test implementation is covered; live sandbox browser acceptance remains open. R0 full finding ledger remains partial. R2 failures/streams/worker/voice recovery is next implementation stage; R3 server idempotency is still necessary. User preferences and new draft semantics are not silently changed.
