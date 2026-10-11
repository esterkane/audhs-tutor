# Consolidated lesson orientation — implementation contract

Status: proposed bounded follow-up to DL-02; not implemented or usability-validated.
Authority: Complete Design System, Learn workspace (page 9) and progressive disclosure
(page 2). Current evidence: DAILY-LEARNING-ACCEPTANCE.md and lesson-layout journeys.

## Concrete problem

At390px the shell, compact SessionControls, LessonContextPanel trigger and separate
SessionBody heading precede the explanation. The concept is repeated in the summary
and heading. The optional composer occupies another full input before Start explanation.
Moving settings below the activity and grouping secondary controls helped ordering,
but does not establish a clear first learning action. Do not close DL-02 on these changes.

## Target composition

One lesson heading, current activity summary, Pause/Focus and Session options, followed
by the current explanation or its explicit Start explanation action. Keep the learning
goal reachable in context and through its existing optional narration. Retain one
composer below the reading content; do not auto-generate, auto-play, silently discard
an input draft, or change the explanation prompt to achieve a layout result.

At empty entry, Start explanation must be usable without entering a question. A learner
must still be able to ask a specific question before requesting an explanation. When
a draft already exists, surface it and make its effect on the next request explicit.
Do not relocate a focused submit button in response to tokens or the first keystroke.

## Ownership constraints to resolve before editing

- Session currently owns SessionControls outside the block-keyed SessionBody. Moving
  it inside that subtree would remount stop/mark mutations on every block change.
  Preserve ownership, pending/error state and stale-navigation guards.
- SessionBody owns local phase and the correctly keyed TeachPanel. Do not derive a
  new page heading solely from a potentially stale server phase or lift the learning
  lifecycle into another client controller.
- TeachPanel owns the composer, stream recovery, alternate representation intent and
  audio activation. Do not duplicate it or mount a second composer in the header.
- LessonContextPanel owns responsive focus/popover behavior. Retain one panel and
  its desktop side column; do not duplicate context for separate breakpoints.

First prototype a presentational composition using existing component ownership,
then review the diff for remounts and focus loss. If preserving owners requires a
structural change, document that choice rather than introducing portals or a second
state store just to save vertical space. No new library is justified.

## Acceptance before publication

Use the same seeded lesson at320/390/1280, light/dark and actual200% Chromium zoom.
Record document coordinates (boundingClientRect.top + scrollY), not incomparable
post-focus viewport coordinates. Inspect the initial viewport and scrolled content.
Verify sequential keyboard traversal, focus restore, optional question before start,
empty start, long/restored draft, streaming cancellation/retry, alternate explanation,
held audio/stop, pause/reload/resume, and actual End/Change topic from options.
Check unchanged checkpoint and absence of unsolicited requests; re-run relevant
Session/TeachPanel tests and browser recovery journeys. Retain code and pedagogy
review gates. Human comprehension/discoverability remains an explicit separate gate.

Likely files: routes/Session.tsx, features/session/SessionControls.tsx,
SessionContext.tsx, LessonContextPanel.tsx, existing lesson layout/focus/recovery
browser tests. Avoid shell-wide changes and unrelated screens in this slice.
