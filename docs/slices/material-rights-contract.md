# M01 proposal — versioned evidence and action-specific permissions

Status: owner policy accepted with stricter origin limits, 2026-10-12. Partial model-provider containment now exists (source-transport-containment.md);
full lineage/export enforcement remains outstanding. Follows
material-rights-inventory.md. This is an application contract, not a legal finding.

## Accepted owner policy — 2026-10-12

The owner approved enforcement with a stricter limit: only content created by the
owner may be sent; explicit third-party learning/course material must not be sent.
This supersedes the broader proposed allowed-permission rule below. Apply the same
boundary to hosted-model transmission and public exports; retain material locally.
Unknown or mixed origin is ineligible. Cached answers, excerpts, translations and
other derived artifacts inherit their inputs' restrictions; rewriting does not make
third-party material owner-created. Access, subscription, attribution, an external
license or a model-generated authorship assertion cannot override this boundary.

Owner-authored text needs explicit, version-bound origin evidence. An own-written
answer may be eligible only if the actual assembled request is free of third-party
course prompts, rubrics, sources and derived context. Do not silently strip necessary
context to force hosted eligibility: keep the complete task local instead.
Local-first routing, task-specific evaluation and existing spending approvals remain
in force; this policy does not authorize new hosted calls. Private archive recovery
is separate from public export and retains its existing owner-authorized scope.

The metadata, assembly-lineage and full enforcement implementation is still outstanding.
Until implemented, this document is not evidence that every runtime path is gated.

## Concrete problem and scope

Document/DocumentVersion/Chunk are shared knowledge records, whereas TutorAnswer
is learner-scoped. Attaching a single allowed flag to a shared document would let
one learner's assertion authorize another learner's hosted request. Saved answers
also need their source lineage retained across reuse; citations alone are incomplete.

Separate shared source identity from learner-scoped evidence and decisions. Preserve
the immutable document version/content hash, existing retrieval and learning logic.
Expected later files: db/models.py, a migration, schemas and a dedicated policy
service, db/backup.py and portability.py, then context/gateway/export consumers in
M02. No changes to mastery, FSRS, curriculum selection or grading are needed.

## Proposed records

1. **Evidence**: immutable ID, learner ID, exact document version ID and content
   hash, evidence kind (observed terms or learner assertion), recorded timestamp,
   reference, bounded quoted terms, attribution requirements and optional expiry.
   Store no credentials or signed URL query secrets. Assertions remain labelled.
   Source checking in C01a can report a changed version; it cannot grant permission.
2. **Decision revision**: learner ID, version/hash, action, allowed/denied/unknown,
   supporting evidence IDs, explanation, policy version, recorded time and explicit
   predecessor ID. Actions are local copying, transformation, hosted transmission
   and redistribution. Access is a separate observation, not permission inference.
   Validate evidence ownership/version and predecessor identity in one transaction.
   Concurrent edits require the expected head; reject stale heads rather than
   silently selecting the newest timestamp. Revocation adds a revision.
3. **Derived lineage**: output identity/version plus input document versions,
   learner-work versions and parent-derived IDs, with a completeness marker.
   Mixed or unresolved ancestry remains explicit. Prevent cycles and bound traversal;
   an exceeded bound is unknown, never permission. A source-free marker requires
   traceable generation inputs, not an empty citation list.

Shared metadata does not expose another learner's private evidence. Reads, writes,
exports and deletion must use learner scope. Do not accept learner IDs from model
output as authority. No LLM decides the effective permission.

## Proposed evaluation rule for M02

| Condition for requested action | Proposed result |
|---|---|
| Every input has a current applicable allowed decision | Eligible for that action |
| Any input has an applicable denial | Ineligible, identify reason without exposing private text |
| Missing, expired, conflicting, hash-mismatched or incomplete lineage | Unknown; require explicit resolution before hosted transmission/public export |
| Mixed allowed and unknown inputs | Unknown; do not silently drop required context |
| Permission revoked after an answer was cached | Re-evaluate on reuse/export; cached permission is not authority |

This does not globally block local learning when historical metadata is unknown.
Local access and transformation policy must be explicit and separately adopted;
unknown hosted eligibility does not imply deletion or an assessment failure.

Evaluate eligibility after assembling the complete input and before any hosted
reservation/request, including fallback, repair and streaming. Bind the decision to
an input hash and policy revision; recheck if assembly changes. A revocation affects
future requests, not already transmitted bytes. Record decision IDs and request hash
without duplicating sensitive source text in logs. Private recovery is not a public
export and must retain that distinction in its UI and manifest.

## Backup, restore and historical data

Use additive tables; migrate no historical record to allowed. Full private backups
retain evidence and lineage. Learner-only backups omit raw corpus but retain bounded
version/hash references and learner decisions; missing restored documents cannot
become eligible through matching a title or URL. Reattachment requires exact hash
and ownership validation. Restore remains into an empty target; backup schema version
must describe new tables. Older backups yield unknown metadata, not implicit grants.
Learner wipe removes private evidence/decisions/lineage without deleting shared corpus
owned by the installation. Validate dangling reference behavior before migration.

## Acceptance before implementation

- Review proposed action/unknown semantics and ownership; record an accepted decision
  before changing runtime gates. No approval inferred from this proposal.
- Metadata slice: immutable revisions, stale-write conflict, wrong learner/version
  rejection, restore of old/new backups and scoped wipe, all on disposable databases.
- Enforcement slice: zero hosted calls for unknown/denied inputs across normal,
  fallback, repair and stream paths; local routing remains usable where permitted.
- Cache/export slice: mixed ancestry, nested notebook outputs, revoked permissions,
  missing parents and cycles; no permission inferred from paraphrasing or attribution.
- UI later shows action, reason, evidence provenance and recovery without forcing
  repeated legal decisions into ordinary learning sessions.

Evidence: inspected current shared Document/DocumentVersion/Chunk models,
learner-scoped TutorAnswer, backup scope and empty-target restore boundaries. This
proposal resolves the shape of the design for review; it does not claim protections
are implemented, and needs no application tests until code changes.
