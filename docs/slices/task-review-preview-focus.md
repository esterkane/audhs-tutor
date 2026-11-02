# Task-review preview focus follows the DOM commit

The narrow task-review keyboard journey failed in CI after the preview heading appeared
without receiving focus. Its animation-frame callback could run before React committed the
heading. A deterministic unit test with an immediate animation frame reproduced the failure.

Preview loading now records focus intent and applies it in a layout effect after the preview
commits. If the learner moved focus while the request was pending, their chosen focus remains.
The existing return-focus control, explicit review confirmation and recoverable save behavior
remain available. No timeouts, assertions or browser retries were weakened to hide the failure.

Verification: nine task-review unit tests passed; the four browser journeys passed in three
consecutive repetitions (12 passes, 21.8 seconds), covering 320/1280 layouts and held preview/save
responses. TypeScript and ESLint passed. The complete isolated upload/author/reading/notes/
feedback/resume workflow also passed (18.8 seconds).
