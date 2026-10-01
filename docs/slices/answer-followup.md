# Continue a saved explanation

Explicitly send a new question from an owned saved answer. Reopening remains read-only. The server loads the parent snapshot and supplies bounded historical context, labeled unverified and possibly outdated; no current retrieval, code execution or mastery is implied. Persist the new reply with its parent ID and the actual supplied context; expose truncation and save failures. Require an active owned session. The UI must support draft recovery, Stop, errors and repeat follow-ups without silently replacing the original answer.

Status: bounded follow-up implemented and verified. Existing local-first gateway handles generation. No new schema migration or independent corpus fact is introduced.

Verification: 437 backend and 217 frontend tests, lint/types/build and four isolated Chromium desktop/narrow history/follow-up journeys pass. Independent code/pedagogy review cleared after adding parent links and inspectable exact historical context/truncation metadata. Draft recovery restores the latest saved parent as well as text; Stop ignores late responses and honestly warns the server may finish. Save failures retain the reply and pause further continuation rather than dropping context. Read-aloud and dictation are opt-in. Build has existing size/WaveSurfer warnings. Synthetic providers do not certify answer quality.

Limits: each request supplies the immediate parent (answer capped at 8000 characters), bounded original workspace and current question. Earlier chat and original retrieved passages are explicitly omitted. No automatic retry/exactly-once inference guarantee; no source freshness verification. The full historical snapshot remains inspectable in the parent chain. Full save-retry, correction and lifecycle work remain queued.
