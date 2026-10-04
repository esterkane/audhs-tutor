# Park header placement — 2026-10-04

The fixed Park trigger covered navigation at320px/200% text in the C1 screenshot. Its fixed success message had the same risk. Both now occupy normal header flow beside audio controls. Capture stays mounted across route changes and remains available on every page, but intentionally no longer floats in the viewport while scrolling. This trades perpetual viewport presence for unobstructed content; the capture workflow, session/skill payload and parked list remain unchanged. The modal now has viewport-bounded height, internal scrolling and wrapping actions.

Changed App.tsx and ParkingLotButton.tsx, with a new parking-layout browser journey. Existing tokens/primitives, no dependency or learning-logic change.

Verification: six unit tests, three parking browser journeys and three shell-orientation journeys pass. Keyboard open/Enter/Escape, draft retention, return focus, one captured request, dialog bounds, trigger above navigation,320/390/1280 at200% text and no horizontal overflow on the original Lesson drafts case checked. Whole frontend lint/types/build pass with existing bundle/worker warnings. Independent read-only review found no blockers/majors and did not execute tests. Narrow rendered screenshot inspected; evidence in ../ux/evidence/parking-header.

Initial parking tests on Preferences exposed separate200% text page overflow at320/390; those failures are not claimed resolved. The regression now isolates the original Lesson drafts obstruction; Preferences reflow stays open. Physical keyboard/VoiceOver, owner preference for header capture, arbitrary parked-list length and phone software-keyboard resizing remain unverified. Existing parking submission failure/duplicate behavior is unchanged and outside this layout slice.

Next: C2 browse-area context, preserving the active session. Full responsive shell and remaining state gaps are still open.
