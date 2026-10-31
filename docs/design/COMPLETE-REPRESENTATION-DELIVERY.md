# Complete alternative explanations and accurate citation metadata

When a learner requested another representation, sentence-tail cleanup could discard a
complete final Python/SQL block, list, or formula. The delivered cache/history then contained
only the introductory sentence. Alternative explanations now retain the entire provider
response, and their output allowance matches the ordinary lesson allowance of 1,600 tokens.
The gateway still reports explicit generation-limit failures; no interrupted response is
silently promoted as complete. This is a delivery guarantee, not factual certification.

New generated cache entries record `representation.complete.v1`. On the next request, an
older generated entry without that contract is regenerated and cached with the new contract.
Existing representation records and saved answers are preserved. Imported legacy
entries without a generation identity keep their existing no-inference behavior. No background
refresh, database migration, session reset, prompt change or model assignment is introduced.

Citation extraction now uses the same Markdown-code masking as unsupported-citation checks.
For example, `items[1]` or a fenced array does not mark source 1 as cited. Actual prose citations
and grouped source references remain recognized. Retrieved source snapshots, owner access,
trust checks and the raw answer text are preserved. Ambiguous unformatted bracketed prose
is outside this fix, as is repairing historical immutable attribution snapshots.

Validation: 142 affected backend tests pass, including fresh delivery, source attribution,
cache refresh, immutable history, private access, source checking and gateway usage/limits.
Strict typing and backend lint pass. Twelve isolated browser journeys cover alternative sources,
knowledge authoring/reading, lesson reading/resume and layout/accessibility across three widths
and both themes. The layout checkpoint assertion now permits only the clock-derived due-review
count to change; all other session fields still must match. This fixes a CI failure when a
review became due during a view-only disclosure toggle, without skipping checks or adding retries. A real local reproduction hit the old
420-token limit; the same semantic example with the ordinary allowance completed and was
saved exactly. Those two smoke timings are not a controlled latency comparison or broad
model-quality qualification. Existing session histories and normal routing remain unchanged.
