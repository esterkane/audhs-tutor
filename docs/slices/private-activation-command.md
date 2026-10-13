# Private activation command

Explicit activation must apply one reviewed draft version atomically and return a stable receipt
on retries. Inputs are owned promotion ID, expected draft version, canonical payload hash and
request key. No inference, API/UI, learning events, mode/energy or accessibility behavior change.

The repository reserves a SQLite write transaction, resolves replay before current draft/source
checks, validates owned promotion and unchanged binding, and validates the complete draft in an
explicit private prerequisite context. Shared validation remains shared-only. Draft aliases map
to fresh private skills; no shared upserts, inferred areas or source permission changes occur.
Header, typed links, content, rubrics and draft publication are one transaction. Failure rolls
back all writes. Read receipts are owner-scoped. No learning evidence or assessment review is added.

Verification: full backend run passed 1621 tests (three dependency warnings). After that run
started, two bounded follow-ups added a consistent receipt read snapshot and missing assessment
source validation; final command/curriculum tests pass all 30 cases, including those changes.
Final type/ruff checks pass; frontend types/lint passed before those backend-only deltas.
Sixteen command cases pass in the sanitized checkout. Code and pedagogy reviews report no
blocker/major; late deltas received bounded code re-review. No browser checks claimed without UI.
Tests cover same/different-key races, changed draft/answer/source, own/shared/foreign prerequisites,
multiple entities, late storage failure, rollback, duplicate mappings, invalid sources, receipt
scope, concurrent receipt deletion and unchanged evidence counts. Private snapshot unchanged.
Next: explicit preview/activation/receipt API, then recovery UI and browser gates. This repository
method is not exposed through a runtime API and authorizes no additional live activation.
