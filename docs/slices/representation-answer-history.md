# Saved alternative explanations

A learner can reopen and search a delivered alternative explanation after its cache row is invalidated.
Snapshot immutable text, representation/object version and original source metadata in the existing owned answer store.
Repeated delivery of the same representation in one session reuses its history record, without new inference or evidence.
Failed saving keeps visible text and uses the existing signed save-only recovery receipt.
Expose the saved-history link and a distinct alternative-explanation filter; preserve optional audio and keyboard controls.
No new mastery evidence, model routing, automatic reuse policy, or learner mode changes.

## Implemented

The existing TutorAnswer store snapshots delivered alternatives, with surface `representation`, skill/area identity, representation/object IDs and generation-time provenance. Identity is learner + session + representation. Cache hits reuse the saved record; invalidating cache cannot delete history. Unknown legacy provenance stays unknown. No database migration is needed.

The session displays local save status and save-only retry; the answer library offers an Alternative explanations filter. A saved representation is history, not mastery or a verified replacement. Existing automatic lesson/workspace reuse policies are unchanged.

## Verification and review

- Full backend suite: 599 passed. Subsequent focused suite: 5 passed, including added concurrent cached-delivery deduplication.
- Full frontend suite: 282 passed; history component suite 9 passed.
- Two isolated desktop/narrow browser journeys pass saved link, provenance, removed-source handling, legacy transition and save-only recovery.
- Lint, strict types and production build passed (existing chunk-size advisory).
- Save failure before and after commit preserves exact text; repeated signed recovery creates one entry without generation. Cache invalidation, FTS search/filter, original source hashes and legacy unknown metadata are covered.
- Independent code and pedagogy reviews: no blockers or majors.

## Limits and next work

This does not deduplicate simultaneous *fresh generation* requests, reconstruct old missing provenance, or imply a saved answer is correct. Save receipts expire after one hour/backend restart. Assessment feedback linkage remains next. Broader real-material quality and latency gates remain open.

Sanitized verification: 19 backend ownership/recovery/representation tests and 13 UI history/save-status tests passed. Previous source-provenance CI passed in both repositories (36948827120, 36948909646).
