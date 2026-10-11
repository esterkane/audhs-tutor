# Home resume alignment

Authority: Complete Design System PDF pp9/12. Bounded slice2026-10-11.

## Inspected problem and implementation

Home already had one Continue action with explicit session-switch confirmation.
The resume card showed the saved topic but only a generic next action; adaptation
proposals appeared as fully expanded competing cards. The Home heading used the
old title size. The checkpoint contains phase, block index and original planned
duration, but not a reliable per-task completed list or time remaining.

Home now uses the page-title token and Home heading. Last time identifies only
the matching saved active concept. ResumeContext shows the recorded running
activity/phase and original planned duration when available; completed/ended
plans and unavailable durations do not produce stale details. This does not
claim time remaining or completed exercises. Existing Continue, preparation and
switch confirmation handlers are untouched. Optional learning adjustments use
the shared native Disclosure on Home, with all original decision handlers and
no empty disclosure when no proposals exist. Other routes retain their current
adaptation presentation. Removed the raw mastery percentage from the optional
new-topic preview; the deterministic prerequisite decision is unchanged.

## Evidence

Baseline four Home resume journeys passed. Twelve affected browser cases passed
on the first validation; two switch checks exposed exact text selectors after
adding Last time. Keeping the lesson title in its own span preserves its identity;
the four resume and two explicit-switch journeys then passed. This totals14
unique affected browser cases (resume, recent material/adaptation keyboard and
large text, session switching, area readiness). Nineteen Home/adaptation/resume
unit tests pass; affected lint and production build pass. Desktop1280 and
narrow390 screenshots inspected;800 also tested. Code/pedagogy reviews found no
blocker or major. No backend, learning-policy or model changes. Original large
bundle warning persists.

## Remaining design work

The PDF alternative trio is implemented in the follow-up below. Keep explicit
switching and due-review caps when refining its presentation. Do not infer a completed-work list
from block position: passed-over/skipped activities are not demonstrated work.
Adaptation dialogs/Preferences controls, the offer branch's heading and remaining
native Home disclosures still need alignment. Cross-theme, actual browser zoom,
screen-reader and owner re-entry/comprehension acceptance remain open. These
bounded tests do not certify the complete Home blueprint.


## Home alternative actions — 2026-10-11

Inspected Review and its backend due endpoint before implementation. Review
already supports a session-bound, capped set outside the planned review block;
entry does not advance/end a lesson, and the empty/completed set offers Back to
the session. Existing explicit rating/finish/continue actions retain their
semantics. Home now presents Quick review, Learn something else (concept map)
and Explore (knowledge areas), after the primary resume/new-session panel.

Quick review performs a fresh bounded current-session read, uses the saved
identity/scope if present, or explicitly starts a session using the click's
settings before opening Review. No block transition/end/rating occurs on entry.
Creation still respects backend area readiness; an empty selected area may
require lesson activation rather than silently broadening the scope. A ref guard
prevents duplicate starts; leaving Home prevents late navigation and cancels the
read. Preferences/goal readiness gates creation, and new-session settings are
locked during the pending action. Continue remains independent and existing
explicit switch confirmation is retained.

Review fixes: fresh lookup initially reused an unbounded query; replaced with
shared15s boundedRead plus unmount cancellation and timeout/retry evidence.
Creation initially allowed pending preferences; corrected readiness/controls.
Code re-review and pedagogy review found no remaining blockers/majors.

Verification: seven new browser cases pass (320/1280 no-write saved-session
entry/return, single creation under repeated Enter, lookup error/retry, timeout,
preferences readiness and leaving during creation). Six existing resume/switch
journeys pass;12 Home unit tests, affected lint and production build pass.
Keyboard tests wait for settings readiness before entering the control; one
initial failure was a premature focus on the intentionally disabled button.
Desktop/narrow screenshots inspected. The fixed bottom navigation scrolls over
content in full-page screenshots; controls remain reachable by scrolling.
No live models, new dependencies or backend changes. Existing large-bundle
warning remains. Actual browser zoom/screen-reader and human choice clarity
are still open; full design acceptance is not claimed.

Next: Preferences switches/segmented-control alignment, plus remaining Home
heading/disclosure consistency and shared cross-theme acceptance.


## Shared disclosures — 2026-10-11

Complete Design System p7: Home now uses the existing shared Disclosure for alternate session, saved material, new-session topic, session options and nested questioning style. This replaces bare summary rows with consistent chevrons and at least 44px targets. Native details behavior, initially collapsed state, mounted children, labels and handlers are retained. No session policy or learning logic changed.

Before: six resume/session-intent browser checks passed. After: twelve affected browser journeys (resume, session intent, late defaults and recent context) and twelve Home unit tests passed, with lint and production type/build checks. Keyboard opening/closing and retained explicit session decisions tested;320/800/1280 layouts covered and320/1280 screenshots inspected. Code and pedagogy reviews found no blockers or majors. Existing build chunk-size warning remains. This does not prove dark-theme, browser-zoom, assistive-technology or human-comprehension acceptance for the whole Home flow. Remaining design work includes semantic typography adoption and disclosures on other screens.
