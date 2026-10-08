# Private correction draft API and command recovery

The stored-draft foundation now has owned, typed API routes for prepare/create, paginated summaries, full authoring reads, save, discard and receipt lookup. There is no publication endpoint and no editor UI yet. Existing read-only report/exclusion screens remain unchanged.

Preparing a correction explicitly enters authoring and includes reference answers, identified in its schema/summary. Ordinary report and draft-list responses do not reveal candidate keys. Source evidence/fingerprints stay private. Create requires an opaque content precondition bound to the original snapshot and question-state revision. Under the write lock it first checks an existing command receipt, then verifies new-command preconditions. Thus exact replay survives a process-token restart without creating another draft; a new create with stale content conflicts. Malformed tokens are422, not server exceptions.

Save may retain incomplete work; typed review problems are returned on the subsequent authoring read, never converted into automatic publication. The UI must not call a successful save validated content. Commands return their original receipt even if a later save/discard has advanced the draft; read the current draft separately. An absent receipt explicitly says the request may still be running: keep the same request identity. Foreign draft/receipt reads and writes return404; no caller-supplied learner identity exists.

## Verification

26 focused tests pass across API, draft storage, structural validation and report discovery. API cases cover create/save/read/discard, lost-response receipt lookup, same-request replay after simulated process-key rotation, stale original content, changed-body conflicts, missing/malformed token, foreign ownership, list omission of answer content and no learning/eligibility writes. Ruff and strict mypy214 pass. Generated API types updated; frontend lint/types and production build pass (existing bundle-size warning). Bounded code/pedagogy review found no blockers/majors.

No schema or rendered UI changes; previous migration and browser/keyboard/layout evidence is reused rather than claiming a new editor journey. Live deployment is limited to backend refresh and read-only endpoint smoke; no real correction draft was created.

## Next

Add an explicit authoring entry warning that references/answers will be shown, a typed editor retaining dirty work, and command recovery with the same request UUID/body. Resolve source and content conflicts without discarding edits. Code execution, listening revalidation, newer-source-version discovery and semantic review remain separate. Ownership/resolver/publication are still unfinished; whole R5 remains open.
