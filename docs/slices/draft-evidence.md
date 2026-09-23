# Draft evidence preservation

Story: reviewing a generated lesson must expose the passages used to generate its objectives.
Inputs: the existing primary-only, prose-ranked lecture passages. Outputs: bounded excerpts with a reserved share per passage, and learning-object citations that retain those selected passages within the existing eight-source cap.
No new schema, routes, UI, learner settings or events; existing model-call logging remains in use. No live draft or publication is changed automatically. Mode, confidence and accessibility behavior remain unchanged.

Reproduced before fixing: a long first passage erased the second selected passage at the 1,600-character truncation; selected evidence after chunk eight was missing from the saved learning object. Both regression tests failed for those reasons.

Scope: this repairs evidence transmission and citations. It does not establish conceptual completeness of notebook-only lessons or validate model-generated MCQs. Thin material still needs owner review.

## Acceptance and review — 2026-09-23

- [x] Every selected passage receives excerpt space within the existing character bound: regression test.
- [x] Selected evidence after chunk eight remains in valid, bounded lesson citations: fake-provider regression test.
- [x] Failed model calls preserve deterministic citations: explicit NoModelReady fallback test.
- [x] Validation: `UV_NO_SYNC=1 make lint`, frontend 42 tests; final `UV_NO_SYNC=1 make test-backend`: 306 passed.
- [x] Private live-model check: architecture section on an online-backup snapshot, hosted providers disabled/budget zero; 8 lessons, no failed groups, all citations resolve. No live publication from this check.

Code and pedagogy review found no blockers or majors. Added the suggested failed-model fallback regression. Remaining minor: equal passage budgets may leave unused space for short passages; proportional redistribution is optional. Notebook coverage and generated MCQ correctness remain human review items.

Separate live curation: the narrative training-data file was marked supplemental and its spurious lesson removed from the unpublished draft. Eight open drafts now contain 22 skills. Original learner-profile, learning-event and session rows matched the pre-operation snapshot.
