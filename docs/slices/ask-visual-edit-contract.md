# Structured visual edit preparation

The editor prerequisite separates editable fields from immutable target/source metadata.
visualEditing.ts extracts bounded title/text/direction/nodes/edges, validates graph
identities and endpoints, and reconstructs saves from the server-provided immutable
base version. Existing part source IDs and document-level restrictions remain attached;
new parts have no fabricated source references. Removing a part does not clear the
base document's source restrictions. Labels remain text for the existing safe renderer.

Recoverable drafts carry document ID, base version ID/content hash and original revision.
Malformed or differently bound drafts fail explicitly. In-progress empty fields or
dangling edges can be recovered but cannot be submitted until repaired. Save checks the
entire UTF-8 command cap as well as field/count limits. It never fetches and substitutes
a fresh revision to make a conflict disappear. No executable code or model calls.

Verification: six focused tests and 668 full frontend tests pass; full lint/type checks
pass; bounded code/provenance review found no blockers or majors. Tests cover retained
provenance, copy isolation, wrong-version/hash/document recovery, partial drafts,
duplicate/dangling graph parts, unknown provenance fields, byte limits and valid cycles.
Backend remains authoritative for ownership, hashes, source policy, current revision,
archive state and transaction semantics. Client validation is not authorization or
factual certification. No backend changes; previous 1557 backend tests apply.

UI is not connected yet, so no new browser-flow or visual-success claim is made.
Next add structured controls/preview, scoped draft persistence, exact-key save recovery,
explicit stale-revision comparison, and browser/keyboard/responsive checks. Keep raw
unrestorable drafts available to copy before explicit discard. Do not erase later edits
when an earlier save finishes. No learning evidence or source permission change follows.
