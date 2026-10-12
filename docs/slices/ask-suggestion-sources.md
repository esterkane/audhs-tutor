# G3a — Source context on saved Ask suggestions

Problem reproduced by inspecting and running the existing Ask suggestion flow:
question controls and Read saved answer give no saved date or source currency.
The existing source-status endpoint already compares hashes and local versions,
but suggestions do not use it. Incorrect/outdated/hidden/replaced answers are
already excluded; retain that policy and explicit opening (no automatic reuse).

Small change: batch the existing read-only source comparison for the bounded
suggestion page; show saved date, why matched, direct-source currency and a
conversation-context caution. Unknown/unrecorded sources stay unverified.
Unchanged text does not imply accuracy, current external information or rights.
No model call, new dependency, migration, grading, scheduling or session change.

Affected files: answer_sources helper, answers API/schema, Ask suggestions and
focused service/component/browser tests. Use existing design tokens and native
buttons/links; keep keyboard selection and narrow-screen wrapping. Full lineage,
review-quality ranking, semantic matching and automatic exact reuse remain later
G3 slices. This slice does not certify or rank factual quality.

## Verification and limits

Batch checks preserve the existing single-answer source-status contract and check
ownership before a corpus query. One query serves at most 100 answers with 100
source IDs each; ordinary history listing does not incur the new comparison.
API regression covers changed/missing/unverifiable/newer sources and no model or
learning-event writes. The ownership/query-count regression and existing saved
answer/feedback tests passed (7 tests). Two component tests cover unavailable status,
unchanged source text, newer versions and earlier-conversation warnings.

Desktop1280 and narrow390 sandbox journeys exercise suggestion labels, keyboard
selection, follow-ups, reload/history and unchanged learning-session state. Screenshots
inspected. Existing negative-feedback exclusion and explicit fresh generation remain.
Required code and pedagogy review reported no blockers/majors. Final labels list
only observed source problems rather than a generic list of possible problems.

No prompt/model or grading change; no local-model accuracy experiment is needed
for this deterministic presentation slice. This is not full G3: quality/semantic
ranking, review-status aggregation, complete historical lineage and exact automatic
reuse remain open. Unchanged means the recorded direct text matches local storage;
it does not establish current web facts, source reliability or model correctness.
Human comprehension and assistive-technology acceptance remain unverified.

Final regression: 1425 passed, 3 warnings in 129.80s (0:02:09). Full frontend 655 passed; final two component checks
passed after test typing/copy correction. Backend ruff/format/mypy and frontend
TypeScript/ESLint passed. Production build passed (existing chunk-size warning).
Final desktop/narrow journeys: 2 passed, screenshots re-inspected after copy change.
Private DB snapshot verified unchanged.
