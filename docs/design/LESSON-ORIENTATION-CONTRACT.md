# Consolidated lesson orientation — implementation contract

Status: bounded heading and initial-entry changes implemented; human usability acceptance remains open.
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


2026-10-11 DL-02 single concept heading implemented: compact session orientation
now owns the one concept h1 above Pause/Focus. Teach no longer repeats the heading
in an otherwise empty card; experiment/error/wait notices retain that card when
needed. Assessment/challenge retain h2 activity headings; movement retains h1.
No ownership, keys, draft, audio or learning logic moved. Unit fixture corrected to
include API active_skill rather than rely on the next recommendation for the title.
Twenty browser journeys pass (layout, Focus, headings, challenge, reading/assessment
return, stream recovery and actual zoom);15 unit tests, lint/types/build and both
reviews pass.390px initial screenshot inspected: Start explanation is visible above
the bottom navigation. Explanation heading document top is658/608/383px at
320/390/1280 respectively, identical in light/dark; not a human comprehension result.
Existing bundle-size warning remains. Empty-entry/composer hierarchy and broader
human/AT acceptance remain open. Logs:/tmp/lesson-heading-{browser,unit,build}.log.


2026-10-11 initial-entry follow-up, before implementation:390px baseline verifies
Start explanation follows the optional composer (lesson-entry-before.log). Use two
explicit intentions: a stable general-explanation action before the input, and Send
lesson question after it. The first uses the unchanged default explanation prompt;
it preserves any draft and states that it does not send it. The second sends only
nonempty input. Only one is primary: general explanation with an empty draft, question
with a draft, and neither after completed content (Let me try remains primary).
Keep both controls at stable DOM positions through typing/streaming; do not hide the
composer, move its owner, change request identity or auto-generate. This is a bounded
presentation/intent clarification, not a learning-kernel or prompt-policy change.
Likely files:Session.tsx, lesson-layout browser checks and targeted entry coverage.

Verification:17 browser journeys pass:320/390/1280 light/dark layout, actual200%
Chromium zoom, keyboard traversal, plan/context/Focus, pause/resume, partial-stream
stop/retry/reload, restored-question preservation with inspected request payload,
reading-to-assessment return and alternate representations. Ten Session component
tests, lint, test/production types and build pass. Code/pedagogy reviews clear;
390px screenshot inspected with Start explanation above the optional input.
No new library, shared token or learning-policy change. Existing large-chunk warning
remains. Owner comprehension, physical audio and assistive-technology acceptance
remain open; hosted CI is still running an earlier commit. Logs:
/tmp/lesson-entry-{before,browser,final,unit,build}.log.
