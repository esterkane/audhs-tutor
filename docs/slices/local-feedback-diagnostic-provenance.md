# Local feedback diagnostic provenance

The local feedback diagnostic uses the production playground message builder and bound response schema, but calls a pinned gateway directly. Its old `live_integration` flag did not explain that distinction. Report version 2 names the runtime builder, prompt version and request intent, identifies the diagnostic gateway task separately from the production task, and explicitly marks production routing and `respond` as unexercised.

The feedback fragment hash now comes through the same prompt loader as the runtime and is labeled as a fragment hash. The previously hashed file is still the current runtime fragment; it was not obsolete. Complete serialized per-case message hashes remain unchanged. Existing immutable result artifacts are preserved. Inference behavior, model pinning, routing defaults, schema validation and paid-provider controls are unchanged.

Two focused regressions verify builder identity and scope metadata, and demonstrate that the component hash follows changed runtime-loader content. Both pass; the explicit-answer-feedback contract suite also passes. Targeted Ruff passes (E402 excluded for the existing script path bootstrap). No real inference, paid calls, database changes or fresh quality result were produced.

Next: evaluate the full runtime response path with a disposable database, pinned local candidates, varied realistic cases and separately reviewed semantic judgments. This metadata change does not complete that quality gate. Integration owner supplies independent review and paired publication.

Integration verification: original focused11 passed; targeted Ruff and format check passed. Independent code and pedagogy reviews found no blockers/majors. No runtime behavior changed, so broad inference/latency checks were not repeated.
