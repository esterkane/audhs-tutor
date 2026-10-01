# Private derived answer-vector cache

The semantic-search foundation stores a bounded vector per learner/answer with the exact answer fingerprint and caller-supplied embedding-model/format key. It is separate from corpus evidence and does not imply correctness.
Writes require an owned unchanged answer and valid finite nonzero vectors (up to 8192 dimensions). Reads are capped at 256 candidate IDs, enforce ownership/fingerprint/model/dimensions and recheck hidden/incorrect/outdated feedback.
Vectors are disposable: deleting an answer cascades to its cache; export/wipe and private backup restore use the existing learner-table lifecycle. A model key change is a cache miss. No model invocation or new API/UI in this foundational slice.
Runtime embedding population and semantic ranking remain next; callers must filter task scope before ranking, compute vectors outside DB transactions and derive model keys from actual model identity/version. No latency or model-quality improvement is claimed.

Migration c16887272890 adds only tutor_answer_vector and indexes. Autogeneration ran outside the watched migration directory; false FTS drops were removed. Copied live DB upgrade/downgrade/upgrade verified preserved FTS and foreign keys before atomic installation.
Verification: 460 backend tests, lint/types, copied-database upgrade/downgrade/upgrade and make migrate-check passed. Migration applied locally only after copied checks and snapshot. Populated two-learner export/wipe and backup/migration suites passed. Independent code/data-lifecycle review found no blockers/majors.
