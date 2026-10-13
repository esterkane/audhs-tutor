# Atomic provisional persistence foundation

2026-10-13. Added isolated owned lookup and staged-result persistence. Serializes on existing owned WorkspaceRequest; validates request fingerprint/session, staged model provenance and current eligible content before writing. Saves one provisional record, completed response and execution phase in one transaction. Replay verifies the stored record; errors roll back all writes. No gateway calls or assessed evidence/schedule writes.

27focused tests pass, including two concurrent workers, replay, failure between record and completion, changed content, foreign ownership, altered answer, non-model route, existing execution and schema regressions. Ruff/mypy pass. This is backend-only, with no user-visible flow changed.

Not yet connected to production: assessed historic outcomes still use their existing path; this isolated function rejects assessed revisions until provisional revision lineage is integrated. Before routing, complete outcome union, advisory event type, revisions, saved-answer/source-policy handling, all learner consumers and continuation tests. The isolation test currently expects no learning events; future advisory event must remain explicitly non-assessed. No deployment or live grading-policy enforcement is claimed.
