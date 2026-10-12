# Visual learning binding — repository reconciliation

2026-10-12. Proposed contract, not an accepted ADR or implemented storage/API.
All thirteen rendering/authoring candidates remain in the research specification.

## Concrete mismatch

`db/models.py:LearningObject` has an ID, skill_id, integer version, goal string,
sources_json and success_criteria_json. `schemas/curriculum.py:LearningObjectIn`
accepts a string goal and lists of criterion/source strings, not objective IDs.
The initial visualization proposal assumed IDs that do not exist. Inventing IDs
would hide a missing ownership contract and break reliable source/version checks.

`kernel/representations.py:invalidate` deletes matching rows regardless of cached
flag. Its store accepts only existing text kinds; diagram means Diagram in words.
`orchestrator/representations.py` already snapshots source metadata, text hashes,
object version, model and prompt version. Reuse that evidence convention, but do
not put immutable authored visual history into the deletable cache.

## Binding without changing learning logic

For a published lesson visual, require exact object_id, object_version and skill_id.
Resolve that object server-side and compare all three. Snapshot the exact goal;
select success criteria by zero-based index plus exact text within that version.
Reject mismatched text, out-of-range indices and references to another skill.
An index is version-scoped, never a globally stable criterion identity. Duplicate
criterion strings remain distinct by index. An object with no applicable criterion
cannot acquire a claimed assessed objective from a model-generated description.

Store source chunk/version identifiers and text hashes resolved from actual source
records, alongside the existing provenance snapshot. A supplied ID alone is not
proof: verify that the source belongs to the bound learning object's evidence.
Missing, changed or unavailable source evidence makes grounding unverified; do not
silently substitute the newest source or object. Retain historical references for
review subject to explicit deletion/retention policy, not automatic cache eviction.

Keep the synthetic leakage prototype explicitly unbound, with its external reference
and authored fixture provenance. It must not impersonate a published LearningObject.
No automatic curriculum publication, inferred mastery or assessment-attempt writes.
The goal and deterministic learning rules are unchanged by representation selection.

## Storage and renderer boundary

A proposed immutable authored-version store needs its own learner ownership,
version/review status, backup/export and deletion contract before a migration.
Representation rows may cache a render keyed by authored version/content hash and
renderer version, but deleting that cache must not delete authored history.
Do not add a generic JSON payload to the existing text endpoint without a versioned
wire contract and client fallback. Unknown kinds fail to a safe text equivalent.

First implementation should validate a bounded relationship payload and its binding,
using existing React Flow after authorization of the storage contract. Other kinds
remain specified extension points; no arbitrary JavaScript/Python/HTML/SVG, remote
loaders or automatic model regeneration. Authored explanations require semantic
review independently of schema validity. Cycles/disconnected graphs may be valid.

## Ordered implementation and acceptance

1. Reconcile V00 ADR: owner-scoped authored lifecycle versus disposable cache,
   backup/deletion semantics and curriculum version binding. Keep status proposed
   until explicitly accepted; no database migration in this reconciliation.
2. Add pure bounded schema and binding validator. Test wrong object/version/skill,
   reordered/duplicate criteria, missing sources, changed hashes, malformed edges,
   excessive payloads and executable/remote fields. Use disposable fixtures.
3. Add versioned persistence/API only after the lifecycle contract is accepted.
   Verify idempotent acceptance/retry, ownership, backup round-trip and cache eviction.
4. Bind a reviewed real learning object; render inline on learner request with exact
   source access, text equivalent and deterministic assessment through kernel paths.
   Test keyboard, narrow/zoom, reduced motion, renderer failure and interrupted work.

This audit inspected current model, schema, kernel, orchestrator and endpoint code.
No app behavior changed, so no browser success or new runtime test pass is claimed.
The existing standalone prototype's browser/test evidence remains in
`visual-learning-prototype.md`. This is a prerequisite clarification, not completion
of V03/V04 or adoption of the complete design system.


## Pure validator foundation implemented — 2026-10-12

`schemas/visual_binding.py` defines the strict bounded `visual-binding.v1` reference
contract. `kernel/visual_binding.py` compares it with server-resolved LearningObject
and Chunk records: exact object/version/skill/goal, criterion index/text, source
membership/version and SHA-256 text identity. Duplicate criterion/source references
and unknown envelope fields are rejected. Repeated criterion text at different
indices remains valid. Missing evidence fails rather than being relabeled grounded.

This is not a renderer payload schema or a production endpoint. It cannot establish
ownership from arbitrary caller-supplied records; the future authenticated service
must resolve them. No schema migration, cache writes, model calls, lesson changes,
competency evidence or UI behavior. Authored persistence remains proposed.

Verification:17 offline tests passed; targeted Ruff and strict mypy on both source
modules passed (`--follow-imports=silent`). Tests cover exact JSON binding, wrong
object/version/skill/goal/criterion, missing/unrelated/changed source records, duplicate
criteria, empty sources, extra fields, coercion and oversized goal. Browser/keyboard
checks are not relevant to this unwired backend-only validator; prior prototype
journeys are not presented as integration evidence.

Independent bounded static code/provenance review found no blockers or majors;
the reviewer did not rerun tests.


## Relationship payload foundation — 2026-10-12

`schemas/visual_relationship.py` implements the first `visual.v1` kind, relationship.
It requires the lesson binding, title, text equivalent, explicit directedness and
bounded node/edge arrays. IDs/endpoints are checked; optional per-part source links
must reference binding sources. Cycles, isolated nodes and self-loops are not rejected
as inherently wrong. No positions, arbitrary styles, HTML fields, scripts, event
handlers or data URLs are accepted. All captions/explanations are plain text, not
executable markup; a future renderer must uphold that boundary.

The bytes parser rejects more than128KiB before parsing; the future HTTP adapter
must also bound request bodies before buffering. Limits:64 nodes,128 edges,240-char
labels,1200-char node explanations,8000-char text equivalent,16 source links per
part. These are implementation limits, not targets for pedagogical complexity.
All thirteen candidate libraries remain in the research specs;
unknown visual kinds are rejected rather than implicitly executed.

Verification:23 relationship cases plus17 binding cases passed (40 total), targeted
Ruff and strict schema mypy passed after an explicit union annotation corrected a
type-check failure. Independent static review found no blockers/majors. No runtime,
UI or persisted content uses this schema yet. Parsing success is not mathematical,
conceptual, source-grounding or accessibility acceptance. Required next integration
checks include text-only rendering and network denial, real source resolution,
reviewed semantics and the existing keyboard/responsive learner-flow gates.
