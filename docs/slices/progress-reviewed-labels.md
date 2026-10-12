# Reviewed task labels in Progress

Implemented and verified. Display-only projection uses frozen learner review authority and exact
criterion checks, never aggregate competency score. Current draft helper requires
all nonempty uniquely identified reviewed criteria to pass with recorded evidence;
keyword/routing checks cannot qualify explanation success. Application attempt is
separate from a passed check. Grading identity and independence-unverified remain.

Eight deterministic criterion tests pass; lint/type checks pass. This helper is not
yet wired into the Progress API or UI. Remaining before activation: task_context
cross-validation, full snapshot/receipt consistency and grading-method validation,
missing/deleted task handling, historical/current exclusion semantics, owner/legacy/
model/partial/revoked projection tests, API types, UI/keyboard/responsive verification
and bounded pedagogy/code review. Keep existing Progress display unchanged until
these gates pass. No commit/publication yet.

Validation delta: projection now requires verified existing task context, validates
the receipt's stored content hash/kind/rubric version, and rejects unsupported
review content. Missing current task becomes historical exclusion rather than a
page failure. Added explanation/application pass/fail, foreign learner, revoked
historical result and malformed provenance tests. Still not exposed through API/UI.
Remaining integrity gate: match receipt's historical assessment content to the
attempt recovery fingerprint (not just rubric version/kind) before activation.
Keep that validation shared with the stable recovery serializer; avoid changing
legacy fingerprints. Integration/browser/review/publication remain pending.

Exact-match delta: moved the unchanged recovery serializer into core/content_versions
with its original orchestrator import alias preserved. Reconstructed the historical
assessment snapshot from the reviewed receipt and compare its hash to the attempt,
including explicit question-state revision. Mismatched content fails closed even if
other provenance fields agree. Optional reviewed_result now projects through Progress
API; generated types updated.40 focused progress/recovery tests and mypy233 passed;
12 qualification cases also rerun after the mismatch regression. Bounded review and
existing Progress browser baseline are running. UI has not been changed yet.

UI/review delta: current eligibility additionally requires current content hash to
match the frozen reviewed hash. Edit+same-facet reapproval remains historical and
excluded; four facet/pass cases cover this regression. UI now shows dated task
labels with current/historical status, exclusion reason, learner-review authority,
model-check source, incomplete help and unverified independence. Existing display
and recorded scores remain.18 focused progress tests, mypy233, backend lint/format,
frontend lint/type/build pass; existing chunk warning remains. Bounded follow-up
review found no remaining actionable findings. Full backend run is live in
/tmp/progress-label-full.log (session33337); collect it rather than restarting.
Browser results and visual inspection/publication still need final confirmation.

## Final verification (supersedes intermediate pending notes)

1310 backend tests passed (3 existing warnings);646 frontend tests passed across127
files. Four Progress browser journeys passed at320/1280px with keyboard disclosure,
retry focus, pagination, saved-answer navigation and no horizontal overflow. Desktop
and narrow screenshots inspected. Browser fixtures are synthetic and use supported
explanation-task context; backend tests verify real receipt/provenance integrity.
Backend lint/format/mypy233, frontend lint/type/build and e2e type checks passed.
Existing production chunk warning remains. Review found and fixed reapproval of
incompatible content incorrectly re-enabling an old record; follow-up has no findings.

Labels are dated, task-specific, disclose learner review and model checks, and
preserve excluded historical results. Legacy/unreviewed records remain unlabeled.
No grading/mastery/FSRS changes, no model calls on reads, no external dependency.
Human comprehension/assistive-technology acceptance remain open. This completes the
bounded display policy, not the wider UX backlog or an independent-learning claim.


## Integrated persistence acceptance — 2026-10-12
Two real HTTP/database tests exercise explicit review, fake-provider grading,
Progress qualification and idempotent replay. Approval after an answer never
qualifies it retroactively; revocation retains the historical label with exclusion.
Reported help remains visible and independence unverified. Replays preserve the
response and learning-record counts and make no second provider call.
Two real Chromium journeys at390/1280 use actual sandbox review endpoints and
storage: approve, reload, read matching approval, revoke, reload and inspect revision2.
Keyboard save/revoke focus and no horizontal overflow pass. The Progress evidence
page remains unchanged by review-only actions. Fixtures create isolated disposable
tasks; no owner database or hosted model calls. This does not certify model quality.
Targeted Ruff/format, frontend ESLint and e2e TypeScript pass. Existing visual zoom
and production-build evidence is reused because runtime/layout code is unchanged.
Human/assistive-technology and full integrated acceptance remain open.
Bounded code/pedagogy review found no blockers or major findings.
