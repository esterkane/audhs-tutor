# Computed evidence for vector explanations

## Problem and behavior

Generated explanations sometimes confuse sufficient and necessary conditions for vector
rankings, or invent contradictory numerical counterexamples. For relevant learner questions,
the existing successful documentation search now includes separately labelled local mathematical
evidence. Original document results and source scope are retained in full. Failed, empty and
unrelated searches are unchanged; the adapter performs exactly one underlying search.

The bounded calculator computes dot product, negative inner product, Euclidean distance and
cosine measures. It rejects unsupported dimensions and nonfinite or out-of-range coordinates;
zero-vector cosine is explicitly undefined. These are floating-point calculations, not database
execution or approximate-index recall measurements.

Examples demonstrate a strict ranking reversal, agreement despite unequal candidate norms,
and agreement with equal nonzero candidate norms. The accompanying reasoning states the fixed
nonzero query assumption and distinguishes sufficiency from necessity. The model still explains
the complete learner request; these examples do not replace retrieval or route broad questions
to canned partial answers. No history is deleted or compressed.

A separate conservative display formatter handles a numbered Sources/Quellen entry explicitly
labelled as a mathematical deduction when its number has an existing document citation. It
shows that metadata reference and preserves the complete original deduction note separately.
It neither verifies the document nor claims that the document proves the deduction. Existing
links, unknown headings, fenced examples and ambiguous entries remain unchanged.

## Verification and limits

The scoped suite passed 400 tests, including source preservation, one-search behavior,
idempotent installation, failed/empty retrieval, numeric bounds, ranking counterexamples and
citation-note preservation. Ruff and mypy passed. English and German isolated hosted browser
journeys passed, including language, lesson state, no-quiz behavior and complete transcript
resume. Inspection of the saved answers confirmed the tested snapshot and vector explanations.
The citation mismatch did not recur in those final answers; its formatting branch is covered
by unit tests rather than claimed as exercised in the final live journey.

This adds no extra model or retrieval call, but increases evidence tokens. It does not establish
a general generation-speed improvement. Format-repair delays, occasional unwanted German
analogies and repetitive check questions remain. The full backend suite passed 3,216 tests with 5 skips (507.55 seconds). The staged
publication scan passed. Passing these examples does not establish universal accuracy.
