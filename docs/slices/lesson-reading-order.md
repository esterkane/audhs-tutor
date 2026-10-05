# Reading-first lesson composition — first slice

2026-10-05. Implements the bounded3b hierarchy work in ux/IMPLEMENTATION-PLAN.md,
following the authoritative design system. DL-02 remains partial, not closed.

## Problem and change

The lesson title followed plan metadata and two optional tools preceded the actual
lesson. Repeated entry instructions further delayed the next action. Existing
screenshots and the new layout journey established this before code changes.

Session now puts the topic heading first within its activity card. Work alongside
and the contextual coding disclosure follow the lesson body. Explanation-entry
copy is shorter while retaining an explicit unprepared state, worked-example intent,
specific-question option and opt-in listening. Pause, End, Change topic, labels,
hints, sources, alternative representations and confidence remain available.
Only JSX order/copy changed; no learning logic, requests, timers, routing, storage,
model prompts, libraries or styling tokens changed.

## Measured evidence

The new ordering test failed against the baseline at390/1280px, then passed after
implementation. Document coordinates of Start explanation on the same empty teaching
fixture:390px moved from1283.8 to1134.2;1280px moved from831.6 to731.6. At320px the
new position is1287.0. These are fixture layout measurements, not measured learning
benefits or proof of owner comprehension. The control is still below the first900px
mobile viewport. Reducing the control stack remains a separate follow-up.

Original:10 Session unit tests pass;6 browser journeys for layout/alongside/coding
return pass, followed by6 layout/partial-response recovery/assessment-clarity journeys.
The final layout test covers320/390/1280px, sequential Tab from Start explanation to
More ways to learn to the question field, native disclosure keyboard use, Pause,
and no horizontal overflow. Narrow screenshot inspected. Lint, TypeScript and build
pass; existing wavesurfer/chunk-size warnings and jsdom canvas limitation remain.
Independent code/pedagogy review found no blockers/majors.

## Remaining work

Optional tools now require scrolling past the lesson; inspect discoverability with
real long explanations before considering a compact contextual shortcut. The current
change does not remove tools or promise they fit above the fold. Continue3b with the
control hierarchy, preserve immediate Pause and active audio Stop, then verify zoom,
screen readers and owner comprehension. No whole-stage acceptance is claimed.

Sanitized verification:10 Session unit tests,3 layout browser journeys, TypeScript
and lint pass with identical layout measurements.
