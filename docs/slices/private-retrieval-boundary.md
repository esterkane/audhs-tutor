# Private lesson retrieval and transport audit

## Existing boundary

`knowledge/reindex._records` indexes Chunk/ChunkProvenance/DocumentVersion, not SkillNode,
LearningObject or Representation. Private lesson activation must not add lesson text to this
shared index: SearchFilters has no learner ownership field. `orchestrator/tools.retrieve` can
widen to the course/corpus; this is existing local corpus behavior, not proof of learner authorship.
Learning contracts and representation caches separately enforce skill/object ownership.

`models_ai/source_policy` refuses hosted/unknown transports. Gateway complete/stream recheck
transport before fallback/repair; direct hosted adapters also refuse. Local speech/vision validate
loopback and local weights. No permission to use hosted models is inferred from private ownership,
editing, activation, an API key or an answer with no current passages. The 53-test existing boundary
sample passed (`/tmp/private-activation-boundary-audit.log`); it is not a complete privacy audit.

## Concrete fix

The runtime Qdrant factory previously accepted remote URLs and default environment proxies.
A shared local client factory now requires loopback, uses REST, disables cloud inference,
proxies and redirects, and suppresses the SDK background compatibility check (a separate HTTP
path without these controls). Runtime construction rejects an invalid URL before embedding lookup.
The synthetic index benchmark uses the same factory. Dependencies and learning logic unchanged;
no UI, evidence, mode/energy or accessibility change. No network/model call used for verification.

## Verification

Final verification:54 focused source/transport tests (including the compatibility-thread
assertion),1602 backend tests,lint/types,benchmark-script compilation and bounded review pass.
No blockers or majors remain. Logs: `/tmp/qdrant-transport-focused2.log`,
`/tmp/qdrant-transport-full.log`, `/tmp/qdrant-transport-lint.log`. Real SDK request behavior is exercised with
an in-process HTTP mock, including an external redirect and proxy configuration. This does not
claim protection against a malicious local server or modified local DNS/network stack.

## Activation prerequisites remaining

Keep private content out of the shared index. Persist immutable activation lineage for the exact
promotion, edited draft version/hash and created skill/object/assessment IDs, then implement the
idempotent owned activation transaction and explicit UI/recovery. Original source history must
remain separate from edited teaching content; activation is neither source permission, assessment
review nor learning evidence. Existing source-state digests track identity/check status, not every
possible same-status source/trust mutation. Private producers remain disabled.
