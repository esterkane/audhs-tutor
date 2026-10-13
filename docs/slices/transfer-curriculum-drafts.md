# Transfer assessments in curriculum drafts

Permit explicit transfer tasks through the existing draft/publish boundary without relabeling them.
Require a nonblank prompt and a nonempty list of distinct, nonblank rubric criteria.
Publication retains the task kind, exact question and rubric. Existing grading, reviews,
evidence eligibility, scheduling and mode/energy behaviour remain unchanged.
No UI or event contract changes; no live lesson activation. Accessibility behaviour is unchanged.

## Evidence
Two regressions failed before the fix: valid transfer rejected, malformed transfer not diagnosed.
Tests cover validation and publication on a disposable database, including exact content retention.
Full backend suite: 1559 passed (three existing warnings). Lint, strict Python typing and frontend type checking pass.
Required bounded code/pedagogy review found no blockers or majors. The approved content
draft is not yet persisted. No screen changed; browser/visual/keyboard behaviour was
not re-tested for this backend-only validation change.

## Remaining integration
The candidate uses separate criterion labels and requirement text. The existing grader
consumes only the criterion string; when converting the approved candidate into a runtime
payload, include the full approved requirement in each criterion. Do not silently drop
requirements or infer that authoring approval is exact persisted-assessment qualification.
No routing, hosted permission or pedagogical scheduling changes are included.
