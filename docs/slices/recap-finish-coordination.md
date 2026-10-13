# Recap completion coordination — AU-RECAP-03

## Problem and change
Before-fix browser checks failed for both Save-first and End-first: separate mutations allowed competing completion requests. First arrival wins on the server, so a bodyless request could win over notes being saved.

Recap now uses the shared session-end hook for both optional-recap Save and bodyless End/Change topic. One synchronous guard and pending state covers all three actions. Fields and competing completion controls lock while pending. Plain End sends no ratings/notes and retains the tab draft; Save sends entered optional values, then clears the draft only through its owned successful callback. Existing history ownership prevents late navigation from taking over a newer view/session.

The pending exit is labeled Return Home and says completion continues after leaving. Normal resumable Pause copy is hidden while ending. The submit control distinguishes Saving from Ending session. No backend/learning-policy change, new library or style tokens.

## Verification
13 component tests cover request payload distinction, duplicate clicks, failure retaining notes, normal/late End, newer session/history ownership and recap storage recovery. Six browser scenarios passed: both competing-action orders, draft reload/save at390/1280 and delayed End navigation at390/1280. Final pending-label change reran both competing-action cases. Keyboard edit/navigation remains covered by unchanged recap/navigation scenarios. Desktop/narrow screenshots inspected; no document overflow.

Code and pedagogy reviews found no remaining blockers/majors after correcting the pending Pause claim. Full backend lint remained green; final frontend lint/type checking and production build passed after removing an unsupported test-locator option. Existing bundle-size warning remains. Logs /tmp/recap-race-*.log; screenshots /tmp/recap-pending-{390,1280}.png. No model calls or live learner submissions.

## Remaining work
Unknown response outcomes across reload and edited retries still need exact saved-recap reconciliation before the full recovery flow can be closed. This slice prevents competing in-flight controls; it does not prove every displayed success matches later edits after an ambiguous response. Plain-End retained drafts are not a durable published note. Outer API transaction and human acceptance remain open.
