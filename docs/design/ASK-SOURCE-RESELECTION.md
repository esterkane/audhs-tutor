# Explicit source reselection for Ask follow-ups

A follow-up retains three recent exchanges and the opening question, but evidence
passages are not attached automatically. SourcePicker currently starts with an empty
search field, so reusing an explicitly chosen reference requires finding it again.
The matched local imputation diagnostic showed better factual fidelity with the
reference present. This motivates easier evidence reuse, not an accuracy guarantee.

Bounded change: inside the existing optional source disclosure, offer Review previous
passages. This shows the immediate saved reply's original passage snapshots as
unchecked choices. Clicking it neither searches nor attaches passages. Existing
selections survive; up to six may be selected. Mark these as historical snapshots
whose text/availability/trust are checked by the existing API when submitted. Keep
exact text for hashing; reject malformed snapshots without reconstructing them.
No automatic retrieval, inference, new endpoints or libraries. No learning, assessment
or model-routing change. Keep private material local under the current source path.

Expected files: SourcePicker, useSelectedPassages (a minimal passage shape shared by
search hits and saved snapshots), Ask prop wiring, focused component/browser tests.
Existing source resolver rejects missing/changed/quarantined passages before model
calls; keep that behavior and request replay unchanged. Validate explicit selection,
no background request, preserving drafts, error recovery, keyboard and narrow layout.
This does not close the larger tutor/checker semantic-quality gate.

Verification: two component tests and two Chromium journeys at 390/1280 pass.
Journeys use API fixtures to assert keyboard preview/selection, no extra search,
reload-preserved draft/selection and identical source hashes on the follow-up.
Both screenshots inspected; no horizontal overflow. TypeScript, targeted ESLint
and production build pass (existing large-bundle warning unchanged). Independent
code and pedagogy reviews found no blockers/majors. Unchanged backend source-change,
availability and quarantine tests provide existing resolver coverage; browser
fixtures do not establish factual correctness. LT2 remains a separate withheld slice.
