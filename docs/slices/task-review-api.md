# Explicit task review preview and decision API

Expose the exact task/objective/rubric for deliberate authoring review,
with the existing opaque content token, latest receipt and whether approval still
matches current content. Confirmation uses repeat-safe commands and owner scope.
No learning events, grading, scheduling or attainment claims change. UI and its
keyboard/responsive acceptance follow; this API does not automatically review tasks.

Implementation files: schemas/task_reviews.py, kernel/task_reviews.py, api/task_reviews.py,
api registration, task-review tests and generated API types. Preserve original
review history when content changes. Unsupported task kinds remain inspectable but
cannot be approved. No model calls or dependencies are needed.

Implemented preview and confirmation endpoints, generated frontend API types, and
focused kernel/HTTP regressions. Preview distinguishes retained historical approval
from approval matching edited content. Confirmation rejects unconfirmed, stale and
foreign-owned requests; retries return the original receipt. 21 focused tests pass;
Ruff lint/format and strict mypy (232 files) passed.
Bounded code/pedagogy review found no blockers/majors and requested that ownership
regression, now included. Full backend suite: 1284 passed, 3 existing warnings,
102.51 seconds. Frontend type checking and production build passed (existing chunk
size warning). UI and live migration remain pending. No attainment claims active.

UI handoff: put explicit review in an optional authoring context, not a new hurdle
before answering. The preview may reveal rubric/solution content, so disclose this
before opening it. Render objective, question and criteria as readable sections;
never evaluate embedded code. Keep confirmation unchecked, distinguish review of
content from success on the task, and show stale/unsupported/revoked states clearly.
Retain the exact command on uncertain network outcomes so Retry cannot duplicate a
review; switching tasks must reset confirmation and reject stale responses. Reuse
existing design tokens and primitives. Verify keyboard focus, 320px reflow, cancel,
rapid submits, timeout/retry and content changes before enabling a visible entry.
