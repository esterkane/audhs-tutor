# Shell orientation — UX26-05 / R7

The learner can identify the current page, return Home, skip repeated navigation with a keyboard,
and find session controls without a misleading claim that a browser-stored session is running.
Current code shows the generic document title, plain links without current-page semantics, no skip
link, and a running label based only on a browser session ID. Fix presentation without inventing a
second session lifecycle. Resume/manage routes through Home's existing server session check.

Acceptance: meaningful title on each route; exact current-page marker (visualizer does not also mark
playground); keyboard skip/route focus; tools remain reachable at narrow widths; remembered session
ID does not claim server activity. Preserve global audio, parking, sensory preferences and all routes.

## Verification and limits — 2026-10-03

Pre-fix tests reproduced missing title/current-page/skip semantics and false remembered-ID running
status. Shell tests now cover exact navigation, route focus and trailing-slash titles. Browser journeys
passed desktop/320px keyboard skip, navigation focus, expanded tools, 200% text, no page overflow,
header-scoped axe AA-tag scan and unknown-page recovery. Project orientation/notebook-return journeys
also passed with the new shell. Live narrow Programs rendering inspected; no learner-state mutation.
Code and pedagogy review cleared; title normalization and consistent Project study label addressed
review minors. No new backend/API/model behavior.

Verification totals are recorded in the handoff. Owner comprehension, full screen-reader/zoom audit
and all-page accessibility remain open. Session link is an action, not an assertion of server activity.
Audio and parking stay reachable. Next UX26-06: clarify playback state and shared audio controls.
