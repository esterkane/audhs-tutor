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

The PDF alternative trio (Quick review, Learn something else, Explore) is not
fully adopted. Before changing those actions, inspect Review's current-session
contract so Quick review cannot silently abandon or advance a saved lesson.
Keep explicit switching and due-review caps. Do not infer a completed-work list
from block position: passed-over/skipped activities are not demonstrated work.
Adaptation dialogs/Preferences controls, the offer branch's heading and remaining
native Home disclosures still need alignment. Cross-theme, actual browser zoom,
screen-reader and owner re-entry/comprehension acceptance remain open. These
bounded tests do not certify the complete Home blueprint.
