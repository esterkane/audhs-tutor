# Local operational notes

Personal inventories, execution logs and handoff history are kept outside the public repository.


## Representation provenance — 2026-10-02

Cached alternative explanations retain supplied-source metadata, citation flags and text hashes.
Legacy entries explicitly report unknown provenance; current passage views are not historical
verification. Backend595/frontend281, focusedAPI4, lint/types/build, two isolated desktop/narrow
journeys and required reviews passed. Browser review fixed duplicate source/audio sibling keys.
See docs/slices/representation-provenance.md. Durable representation answer history and assessment
linkage remain next; this is a prerequisite, not completion of saved-answer path coverage.


## Representation answer history — 2026-10-02

Delivered alternative explanations now enter searchable immutable answer history. Cache invalidation
cannot delete them; cache hits reuse the learner/session/representation entry. Save failures retain
text and signed save-only recovery. UI includes saved link and distinct history filter. Full backend599,
then focused5 including concurrent cached delivery; frontend282, lint/types/build, two desktop/narrow
journeys and required reviews passed. See docs/slices/representation-answer-history.md. Assessment
feedback linkage is next; fresh-generation request deduplication and broader quality remain open.


## Assessment session ownership — 2026-10-02

Both assessment routes now require the current learner to own the supplied session before next-item
generation or grading. Regression reproduced foreign-session 200 responses, then verified equal
404 responses and no attempt/evidence/memory/event/model/history changes after rejection. Backend602,
lint/types, sanitized focused6 and code review passed. See docs/slices/assessment-session-ownership.md.
Next: saved assessment feedback linkage without regrading or duplicate learning evidence.


Assessment ownership follow-up: challenge start/submit now have the same ownership guard. Two pre-fix regressions reproduced; focused12 and lint/types passed, code review clear. All four grading entry routes identified in this audit are guarded. Saved assessment feedback remains next.


## Saved assessment feedback — 2026-10-02

Shared Grader now saves completed feedback and original visible question/answer/result, linked to
the attempt. All four result surfaces expose saved history/retry. History is searchable with readable
past grading details; personal feedback is excluded from default suggestions and automatic reuse.
Recovering a failed save never regrades or adds evidence/reviews. Full backend608/frontend282, focused
backend5/UI14, lint/types/build, two desktop/narrow journeys and required reviews passed. See
docs/slices/assessment-feedback-history.md. No old-attempt backfill or grading-request idempotency
claim; broader quality, material coverage and UX queues remain open.
