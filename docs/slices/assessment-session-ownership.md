# Assessment session ownership

The assessment next-item and submission routes must validate the active learner owns the supplied session before item generation or grading. Missing and foreign sessions return indistinguishable 404 responses. Rejection must not write attempts, competency evidence, memory, events, model calls or saved answers. Internal grading remains available for trusted local evaluation callers. No UI or pedagogy behavior changes for valid owned sessions.

Regression reproduced on disposable test databases: both routes previously returned 200 for a foreign session, including a graded attempt. The boundary now uses the existing get_owned guard.

Independent code review found no blockers or majors. Focused ownership suite: 6 passed; full backend suite and lint/types recorded below after completion. Existing valid-session assessment tests remain the positive-path coverage; no UI change requires a new browser journey. Saved assessment feedback linkage remains next, and this guard does not provide grading-request deduplication.

Final verification: 602 backend tests passed; lint/strict types passed; sanitized focused ownership suite 6 passed. No live learner data was used by regression tests.
