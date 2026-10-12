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
