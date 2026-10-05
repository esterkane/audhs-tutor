# Browser contract repairs and narrow Home controls

2026-10-05, bounded follow-up to tutor streaming verification.

## Problem and scope
Canceled remote browser runs exposed real failing journeys: collapsed Home topic controls, the narrow navigation menu, and companion fixtures that intercepted only buffered replies after ordinary tutor replies moved to SSE. An expanded Home test reproduced overflowing session choices at 320px with 200% text sizing.

## Change
Open the existing disclosures/menu in journeys and mock the actual streaming endpoint, preserving request identity, retry, and mounted-node assertions. Home's three Choice groups now opt into container-responsive stacking. Labels wrap without truncation; all options, callbacks, defaults and learning logic remain unchanged. Other Choice users retain their column layout.

## Evidence
- 16 affected browser journeys passed; final expanded zoom/keyboard scenario also passed.
- Inspected the narrow, 200% text-size mode-control screenshot: all three choices readable, Low capacity selected without clipping. This is text sizing, not actual browser zoom or a general accessibility certification.
- Full frontend: 517 passed; lint and TypeScript/production build passed. Existing bundle-size warning remains.
- Initial full frontend run had one Review checkpoint/reload failure. The unchanged focused suite passed 13 tests and unchanged full rerun passed 517. Cause is not established; retain as a reliability follow-up if it recurs.
- Independent bounded code review found no actionable issue.

## Remaining
The complete remote browser suite has not yet passed; earlier runs were canceled by subsequent pushes. Let the next full run finish and diagnose any remaining failures. No claim that the whole UX, accessibility or latency acceptance stage is complete.
