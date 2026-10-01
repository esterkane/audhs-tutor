# Explicit saved-answer reuse

Learners may opt into reopening an exact matching workspace reply without generation; default remains fresh generation.
Match owner, target/context, full supplied question, code, output, exercise, intent, history and prompt version. Exclude negative feedback and memory-derived responses. Reject referenced sources with missing/changed/unverifiable text or newer local versions.
Return the original answer ID, text and timestamp with an explicit historical label. No new learning event, saved row or model call on reuse. This does not establish external dataset freshness or factual correctness.
UI option is keyboard accessible, disabled while busy and reversible. Prior replies remain inspectable; fresh generation is always available. All modes preserve their supplied teaching intent.
Verification: 443 backend tests plus four focused memory/reuse cases after the final source guard test; 224 frontend tests; lint/types/build and two isolated desktop/narrow notebook journeys. Independent code/pedagogy review found no blockers/majors. Tests prove skipped model calls and no duplicate answer row, not real-world latency or teaching quality. Lookup is deliberately conservative (bounded literal candidates); semantic matching and broad streaming tutor integration remain separate.
