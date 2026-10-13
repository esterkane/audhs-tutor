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
draft has now been persisted locally without activation (details in private handoff). No screen changed; browser/visual/keyboard behaviour was
not re-tested for this backend-only validation change.

## Remaining integration
The candidate uses separate criterion labels and requirement text. The existing grader
consumes only the criterion string; when converting the approved candidate into a runtime
payload, include the full approved requirement in each criterion. Do not silently drop
requirements or infer that authoring approval is exact persisted-assessment qualification.
No routing, hosted permission or pedagogical scheduling changes are included.

## Inactive draft preparation
Runtime payload `docs/design/review-candidates/leakage-runtime-draft-v1.json` preserves the
approved content with full requirements in each criterion. Pydantic validation, disposable
copy save/readback, live save/readback and HTTP readback pass. Assessment, learning-object
and attempt counts were unchanged. Bounded content review found no blockers/majors.
Browser inspection found that the current draft screen gates drafts behind a course
selection, hiding course-independent authored drafts. Next: provide an explicit review
entry for those drafts without auto-activation. No frontend code changed in this slice.
