# Review help bound to question content

Completed 2026-10-13.

## Problem and change
Legacy session/item-only help counts could hide Good and Easy on a revised review card. Review now keys help storage and the QuestionHelp component by session, item, content version, question and options. Existing unversioned counts remain in browser storage but are not attributed to the revised card. Current-version counts still restrict ratings and are sent with the rating request. No grading, scheduling, confidence or independence policy changed.

## Evidence
- Regression reproduced before the fix: Good was absent when legacy help count was three.
- Review and QuestionHelp: 27 tests pass, including current-count preservation and late help completion isolation.
- Real sandbox review conflict → explicit refresh → reveal → rating: two browser journeys pass at 390 and 1280 pixels. Legacy count does not contaminate the accepted request (hint_count=0); keyboard Enter submits; no horizontal overflow; screenshots inspected.
- Targeted ESLint and production build/type checking pass. Existing bundle-size warning remains.
- Bounded code review found no blockers or majors.

## Remaining
The pre-existing stale-error paragraph remains visible after explicit refresh, despite the revised card being ready; record and address separately. Broader R4 and assessment-quality policy remain open. This test does not establish model accuracy or independent learner performance.
