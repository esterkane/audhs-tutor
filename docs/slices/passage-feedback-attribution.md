# Passage-based feedback attribution

Workspace prompt v12 uses a private internal selection schema: the model chooses a labelled
passage from the current learner answer. Application code inserts its exact text and validates
the unchanged QuotedFeedback contract before rendering and saving. The model no longer has to
retype a quotation. Prompt fragment quoted-feedback.v3 and structured-repair.v3 describe selection.

Passages retain exact start/end offsets, are at most 400 characters, prefer whitespace boundaries,
and cover every non-whitespace character of the bounded answer. IDs are bound to answer content.
Unknown IDs, selections from a different answer, repeated selected text and forbidden follow-ups
fail validation. Full answer context remains visible; learner text is never embedded in the schema.
The original request, selected IDs, passages and final literal feedback are retained privately.
Pre-v12 exact replies cannot silently replay under the new contract. No model route changed.

Attribution is not correctness. Long passages can split a qualification; the model must interpret
them in the full answer. A short answer has one passage and one finding, whose explanation must
distinguish mixed correct/incorrect claims. Correct IDs do not prevent bad mathematics, false
execution claims, unsupported citations or unwanted questions in other fields.

Verification: 691 backend tests passed; strict mypy passed 187 app files. Focused coverage includes
Unicode, whitespace, 8000-character answers, repeated passages, request isolation, schema privacy,
exact reconstruction, saved public feedback and runtime diagnostic compatibility. Independent
code and pedagogy reviews found no blockers/majors.

The eight-case synthetic local runtime run delivered all eight responses on first attempts. Manual
review: three pass, four partial, one semantic failure. Previously failing cleaning feedback now
delivers an exact quotation but still misses numerical reasoning. The bin-boundary response is
still wrong. These results support a bounded delivery improvement, not broad tutor correctness.
Additional direct-gateway cases are recorded separately and cannot prove runtime-path behavior.

All 13 additional direct-gateway cases passed attribution validation, including long answers,
quoted mistakes and untrusted instructions. That diagnostic bypasses runtime respond and production
routing. Manual semantic inspection remains separate: a correctly selected quote can still be
misinterpreted, and the long-answer case is not a maximum combined-context capacity test.
The passage table duplicates bounded answer text in model context; no general context-budget claim
is made. Sanitized checkout independently passed 62 focused tests, full Ruff and 187-file mypy.
