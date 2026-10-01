# Voice session exclusivity after interruption

An interrupted model may take longer than the cooperative cleanup timeout. While its task
still owns the shared async database session, typed requests, session restarts and speech
must not start competing work or replace the task reference. Rejected work is not queued or
retried automatically; the learner receives a literal wait message. No new model routing,
learning events, mode/energy adaptations, microphone or playback behavior is introduced.

Regression reproduced: text replaced the old task after the cleanup timeout; restart entered
session/preference queries while the prior response was still active. A common wait guard now
covers text, restart, speech transcription and barge-in. Prior task identity is preserved.

Verification: full backend579, focused voice tests and lint/types passed. Required code and pedagogy reviews found no blockers or majors; rejected requests explicitly state they were neither started nor queued. Tests use synthetic mocks/fakes, not real provider timing. This is a prerequisite to request identities, not durable voice retry.
Connection teardown while providers resist interruption remains a separate lifecycle concern;
server turn identity and recovery retrieval still require implementation. Personal voice gate
remains open.
