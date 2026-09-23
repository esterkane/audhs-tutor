# n8n workflow source ingestion

Story: search downloaded workflow templates alongside their course notes without running them.
Input: recognizable n8n JSON exports, including ZIP members. Output: node names/types, parameter names, edges with ports, and teaching notes; existing document provenance and trust rules apply.
Credentials, parameter values, pinned/execution data and workflow settings are omitted. Code and expressions are never evaluated; notes remain untrusted evidence.
No schema, UI, model route or learner-state changes. Existing ingestion outcomes/progress/resume are reused; mode and accessibility behavior are unchanged.
Limits reject oversized or malformed workflows honestly, rather than silently dropping nodes. General JSON datasets stay unsupported.

## Review and acceptance

- Code review: no blockers/majors. Both minor findings fixed: size-limit failures classify as gated, and edge/output/text/input-port boundaries have regression tests.
- Thirteen focused tests cover structure/notes, credential and runtime omission, malicious notes remaining flagged, unrelated JSON/link dispatch, malformed/oversized inputs, blank notes, ZIP provenance and idempotent repeat import.
- Source parser uses existing `code` type and format metadata `n8n-workflow-v1`; no dependency or migration. Raw-file hashes preserve ordinary versioning. Previous one-run structure imports in the private course-resume tooling remain historical versions of the same URI where applicable.
- This is structural evidence, not a complete explanation of each node's configuration. Parameter values and embedded scripts remain only in the original JSON. Limits: 1000 nodes, 5000 edges/output slots, 250000 extracted characters, 16000 per note.

## Validation — 2026-09-23

`UV_NO_SYNC=1 make lint` and `UV_NO_SYNC=1 make test`: backend 319, frontend 42 passed. Live no-media import of the existing n8n course: 239 imported versions (some replace the earlier one-run structure summaries), 117 unchanged, 1 reference-only, 6 unsupported non-n8n JSON, 2 gated images; zero parser/access/retryable errors. 1414 unique chunks indexed, 3108 duplicates avoided. Course-filtered real retrieval returned three code hits in the requested course. SQLite quick check and foreign keys passed; learner profile, 33 learning events and seven sessions unchanged against the pre-import snapshot. Originals and private snapshots remain outside Git.
