# Project tutor structured transport

The imported tutor requests Markdown followed by a protocol footer. The host gateway
instead requires a structured response with answer prose in `text` and metadata in
`state`. Supplying both instructions can cause duplicate footers and repair attempts.

The adapter now reconciles only those two transport instructions in the complete,
pinned runtime/schema sections. All field rules, teaching policy, persona, mode,
citations, tools and examples remain byte-for-byte unchanged. Unknown, incomplete or
ambiguous prompt sections are preserved. Stored conversation messages and source
results are not rewritten. Output allowance and routing are unchanged.

Verification:

- 289 Supabase backend tests, including exact reversible policy changes, optional
  persona, unknown/repeated sections and complete unchanged history.
- Ruff and strict mypy (350 application files).
- Five isolated browser journeys covering incident handling, reviewed explanations,
  source-based answers and complete transcript resume in German and English.
- Full uploaded-source → research → authored lesson → reading → notes → feedback →
  resume browser journey.
- A small paired real hosted evaluation retained correct answers and full histories.
  English elapsed time was 8.443s before / 6.044s after; German 9.434s before / 8.819s
  after. These single pairs do not establish a general latency improvement or broader
  local-model factual qualification. No context, output ceiling or safety gate was reduced.

This addresses contradictory transport instructions, not general factual accuracy.


The paid browser regression exposed a complete-answer loss during format repairs.
A complete terminal protocol footer is now reused when all metadata fields validate
and match the supplied state. If the outer state is absent, the complete validated
footer can supply it. Conflicts, partial objects, trailing prose and missing answers
still fail validation. No prose is rewritten or reconstructed from a summary.
Metadata JSON alone is rejected as a final answer.

A gateway regression proves that a matching complete footer takes one attempt and
preserves every character. The real hosted browser journey then passed provider
setup/failure, two fresh answers, full transcript reload and budget-blocked provider
reselection. The final run took 26.8 seconds including stack startup; both actual
answers were inspected for the requested transaction and vector-search distinctions.
Earlier failures are evidence for the fix, not successful test runs. The general
local-model factual-accuracy work remains open.
