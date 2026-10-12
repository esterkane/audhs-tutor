# Lesson draft navigation recovery with denied storage — R4

An unsent lesson question must survive Pause/return within the running tab even
when sessionStorage writes fail. Existing session/block/skill identity stays fixed.
No automatic submission, model call, learning event or change to grading/scheduling.
The existing status text explains navigation-only retention and reload limitations;
keyboard controls and sensory preferences stay unchanged.

## Reproduction and implementation
A remount regression failed with old persisted text replacing the newer failed-write
draft. The hook now keeps only unsuccessful writes in a tab-memory map under the
existing scope. Successful persistence clears its fallback; failed empty writes keep
an empty tombstone so older saved text cannot reappear. No destructive purge policy
is introduced. A full reload/tab closure still cannot recover a failed browser write.

## Evidence
26 focused hook/Session tests and the full frontend suite pass (647 tests).
Six isolated browser cases pass: existing reload/partial-stream behavior plus
390/1280 storage-denied Pause/return, exact text, explicit emptying and zero tutor
requests. Targeted ESLint, application/e2e TypeScript and production build pass.
Desktop/narrow screenshots inspected; existing layout and focus remain intact with
no horizontal overflow. Narrow warning lies below the initial viewport and remains
reachable; no whole-screen discoverability or assistive-technology claim.
Bounded code/pedagogy review found no blockers or majors. Existing bundle warning
remains. Backend unchanged; previous backend evidence reused.

Remaining: reload recovery when storage is unavailable needs a separately designed
durable store. General R4 content-version recovery and human acceptance remain open.
Logs: /tmp/lesson-draft-{before,after,browser,build,full}.log.
