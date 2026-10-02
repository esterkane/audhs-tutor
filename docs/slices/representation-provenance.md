# Representation source provenance

Cached alternative explanations now retain the source IDs, labels, warnings, citation usage and SHA256 hashes of the actual passages supplied at generation. The API returns the same snapshot on cache hits without retrieval or inference. Existing rows migrate with empty provenance and are explicitly labeled unknown; no historical sources are invented.

The session source disclosure distinguishes context supplied from sources cited. Opening a passage displays the current local copy, not a historical text snapshot or verification. Removed sources retain their citation and existing missing-passage UI. This slice does not yet make representations durable searchable TutorAnswer records; that remains next, followed by assessment linkage.

## Verification

- Backend full suite: 595 passed. Frontend full suite: 281 passed.
- Focused API regression: 4 passed, including changed passage after generation, cache parity, actual citation flags and unknown legacy provenance.
- Lint, strict types and production build passed (existing bundle-size advisory).
- Two isolated desktop/narrow keyboard browser journeys passed: cache sources, missing passage, focus return, switching to legacy unknown state.
- Additive migration a42e7f90d821 validated on a disposable snapshot before publication; live revision verified.
- Code and pedagogy reviews: no blockers or majors. Browser testing exposed duplicate sibling keys for source disclosure/read-aloud; namespaced the disclosure key and reran both journeys successfully.
- Minor follow-up: source viewer currently retains trigger focus when opened; consider moving focus into its region consistently across citation surfaces.

Sanitized checkout: 23 focused API/migration/backup tests and 2 component tests passed; publication guard passed. Both remote repositories verified private. Live database foreign-key check passed.
