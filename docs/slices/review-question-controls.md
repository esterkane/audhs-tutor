# Review question practice controls

Learners can explicitly exclude or restore an assessment-backed review question using the existing lazy question controls. Vocabulary cards have no assessment control. The API exposes only the linked assessment identifier, using the existing owned snapshot.

A confirmed choice leaves the displayed card and tab-local notes in place, disables rating, and asks for an explicit queue refresh. Failed refresh preserves the card and offers retry. Successful refresh releases the frozen card and focuses the review workspace, without adding a reviewed ID, clearing notes or writing learning evidence. Mode, energy, scoring, mastery and scheduling policies are unchanged; no new model call or dependency.

## Evidence

- API eligibility/content-version tests: 19 passed, including linked versus vocabulary identity.
- Review/shared-control component tests: 20 passed, including failed refresh, saved notes, unchanged reviewed IDs and blocked rating.
- Real isolated sandbox browser: desktop and 390px journeys passed; keyboard open/refresh, focus recovery, no horizontal overflow, explicit exclusion with real local API. Both screenshots visually inspected. No paid providers or live learner database used.
- Ruff, mypy (207 files), frontend lint and production build checked. A test-only unsupported Testing Library option was found by TypeScript and removed before final verification.
- Bounded code/pedagogy review: no blockers or important findings.

## Remaining

Dedicated code/challenge/listening entry controls and the correction/replacement workflow remain open. Other-tab changes still rely on server version/eligibility rejection and existing receipt recovery. No new owner-comprehension, physical-audio or screen-reader acceptance is claimed. Existing production bundle-size warning remains. Remote CI must finish independently.
