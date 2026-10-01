# Saved answer source text checks

Learners can explicitly compare saved source fingerprints with the local corpus before reusing a reply.
GET /answers/{id}/source-status is owner-scoped and read-only, bounded to 100 references, with an omitted count.
It distinguishes unchanged, changed, missing and unverifiable text, independently flagging newer local document versions.
No model call, learning evidence, mastery update or internet verification occurs. All modes share the same optional action.
The button supports keyboard use and announces results; failures remain retryable. Text matches never certify answer correctness.

Verification: 440 backend tests, 221 frontend tests, lint/types, production build and two isolated desktop/narrow keyboard browser journeys passed. Independent code/pedagogy review found no blockers or majors. These are synthetic contract checks, not proof of answer accuracy or latency improvement.
This is a prerequisite for retrieval-before-generation, not automatic saved-answer reuse or semantic search itself.
