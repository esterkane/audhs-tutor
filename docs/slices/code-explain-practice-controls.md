# Linked code explain-back practice controls

The main coding question already supported exclusion/restoration, but its linked explain-back question did not. Learners can now exclude or restore that question independently, keeping their code, run results, answer and exposure to hints/solutions. No learning policy, grading, provider, schema or backend change. No new learning event is emitted by these controls; existing question-state endpoints retain their receipts.

After an acknowledged change, checking the linked answer is disabled. Restoration requires an explicit bounded refresh that verifies both exercise and question identity and a fresh question token. Only linked question fields change; failed refresh preserves work and offers retry. Unmount cancels the request. Primary code submission remains independent. When a solution and successful code grade coexist, only the solution's explain-back form is displayed rather than two duplicate answer forms. Controls use existing tokens and optional confidence; no mode/energy change.

## Verification

- Inspected the existing linked submission and both form entry points before changing code; identified missing controls rather than a grading defect.
- 12 focused component tests pass, including independent exclusion, failed/successful refresh, retained code and answer, retained run eligibility and fresh-token submission. Existing solution disclosure and main code controls remain covered.
- Four isolated Chromium journeys pass: new linked controls through explicit solution disclosure at 390/1280 widths, plus existing primary code controls. Real sandbox question-state/read APIs; no model, coursework submission or live database. Keyboard disclosure/refresh and restored focus checked; no horizontal overflow; both screenshots visually inspected.
- Frontend lint/types and production build pass. Existing canvas-test and bundle-size warnings remain.
- Bounded independent code/pedagogy review found no blockers or major findings.

## Remaining

This does not add reload persistence for the existing explain-back draft. Previously excluded linked questions without an actionable ID still use exclusion management. Reviewed correction/replacement, integrated human comprehension and full accessibility acceptance remain open. No claim of whole R5 completion.
