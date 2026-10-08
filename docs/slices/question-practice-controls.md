# R5 — explicit question exclusion and restoration

Story: during an ordinary lesson question, preview the review impact, explicitly exclude it from future practice, and later find/restore it in Preferences. Reporting question quality remains a separate action.
Input: assessment identity, current eligibility revision, request UUID and optional reason. Output: acknowledged state; no score, mastery or automatic replacement. The earlier selector/review/grading guards enforce eligibility.
Reads are lazy and bounded. No new library, model call, autoplay, mode or sensory-preference change. Past answers and review schedules remain intact.

## Implementation

- Typed `/api/questions/{id}/practice` preview/action endpoints and paginated `/api/questions/excluded`. Preview includes public wording, skill title and active referenced review-card count, excluding vocabulary and other learners. Hidden answers/rubrics are not returned.
- API action closes dependency reads, then commits state and repeat-safe receipt together; failure rolls back. Expected revision prevents stale actions; same UUID/body replays its acknowledged result.
- Ordinary Session question controls show status/impact before an explicit Exclude or Restore. No requests are sent just by rendering the closed control. Reporting a bad question does not perform exclusion.
- Uncertain writes retain exactly the original request for explicit retry. Conflicts require a fresh read. Rapid duplicate activation is blocked synchronously; reload reads status without resubmitting. Read/action timeouts do not imply failure to commit.
- After an acknowledged change, the current ordinary question cannot be submitted until a fresh question is chosen; its answer draft is retained. The control never auto-advances a lesson or submits an answer.
- Preferences contains paginated exclusion discovery. Restoration refreshes the list and moves keyboard focus to its stable heading, with an acknowledgement; no stale excluded count remains. Links beside question controls reach this section.

## Verification

Backend API tests cover impact count, learner/vocabulary isolation, idempotent replay, stale revision, list/restore, missing ID and pagination validation. Three UI tests cover explicit preview/action, stable uncertain retry, rapid duplicate clicks and conflict refresh. Two real sandbox browser journeys at390/1280 cover lesson exclusion, disabled submission, discovery after reload, keyboard restoration, stable focus and no horizontal overflow; screenshots visually inspected.

Full backend969 tests and frontend553 tests pass, plus Ruff/mypy207 and frontend lint/types/build. Existing backend warnings and bundle-size warning remain. Final small toggle-label/focus refinement is covered by the focused UI/browser rerun. Bounded code and pedagogy/accessibility review found no blockers or majors.

## Remaining scope

R5 is not complete: reviewed replacement/publication and correction inbox remain. The visible exclusion entry is currently on ordinary lesson questions; dedicated challenge/listening/code/review entry controls remain future adoption, although their backend selection and write paths enforce exclusions. Human comprehension, screen-reader and actual browser-zoom acceptance remain open. The impact count describes current active linked cards, not a promise about a future exact count.

Logs: /tmp/question-controls-{api,ui-tests,browser,backend-full,frontend-full,ruff,mypy,ui-lint,build}.log. Screenshots: /tmp/question-exclusions-{390,1280}.png.

## Live activation

Confirmed zero running imports and no established port8000 connections before gracefully stopping the owned backend. Created a SQLite backup with integrity_check=ok under the private temporary directory, applied previously verified migration6b53cfd352a8, restarted the backend and confirmed health200, exclusion-list200 and schemahead. Live exclusions remain empty; only sandbox questions were changed. Frontend HMR serves the controls.

The empty-question view now says no questions are available and links to exclusion management, rather than implying content has never been created.

Final ordinary-session/control regression subset:13 tests passed; final lint/types/build passed. Full suites preceded the small empty-state wording and callback wrapper refinements; backend remained unchanged.
