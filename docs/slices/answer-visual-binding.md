# Answer visual binding — G4 foundation

Bind an optional authored visual to the exact saved Ask question, answer and private
conversation/source history, without fabricating a lesson objective or learning evidence.
Inputs: owned answer ID and optional author-intended purpose. Output: strict binding,
immutable serialized private snapshot, lineage issues and per-answer source currency.
No events, model calls, UI, migration or learning-state writes. Mode/energy unchanged;
no new interaction or accessibility surface in this backend foundation.

Accepted lifecycle: ../design/AUTHORED-VISUAL-LIFECYCLE.md. Existing lesson binding
and renderer contracts stay unchanged. This read is not an acceptance receipt;
future writes must resolve inside their transaction. Currency is not correctness
or permission. Missing/legacy/cyclic/bounded lineage stays unknown, never owner-authored.
All ancestors are traversed up to 32 records and 2 MiB of private serialized records;
size overflow fails explicitly. Source-free complete records are ungrounded.

## Verification and review

- 41 focused answer/lesson binding tests pass, including ownership, full ancestry,
  stale ORM identity maps, pending edits, original timestamps, limits/cycles,
  missing and changed sources, historical source versions and strict schema.
- Reviewer found two majors: same-text source-version reassignment and a sourced
  request whose snapshots were lost. Both reproduced as failing tests, fixed and
  rerun. Re-review reports no remaining blockers/majors.
- No browser/keyboard/responsive change: this foundation has no runtime consumer.
- Final full backend: 1463 tests passed. `make lint` passed (Ruff/format, strict
  mypy 253 source files, frontend TypeScript and ESLint). No live model call used.

## Limits and next step

The result is not a durable review, accuracy certification or outbound permission.
Source checks preserve historical version identity; a newer version alone does not
silently replace it. Future acceptance must additionally apply current trust/rights
policy in its write transaction. Complete traversal is capped; truncation is reported,
not treated as complete. No change to existing lesson wire payloads.

Next: immutable storage, backup and learner wipe
before a write API or inline visual generation. No generated visual approved here.
