# Optional project check questions

Explicit standalone requests such as “No SQL or quiz.” and “Bitte kein Quiz.” suppress the lesson check question for that turn. The request does not change session mode, stored history, assessment or Socratic defaults. Local reviewed answers and fresh hosted explanations honor the same constraint.

A request-local context overrides only the missing-question guard. Citation, factual, execution and other checks remain active. Quoted, fenced, negated and descriptive mentions do not activate the exception. This parser intentionally supports bounded explicit directives, not every paraphrase.

The hosted transport can recover an accidentally serialized whole response inside its text only when the nested metadata validates and exactly matches the outer metadata. The complete inner prose is preserved. Conflicting metadata is rejected; ordinary JSON examples are unchanged.

Validation: 328 scoped backend tests; Ruff formatting/lint; mypy across 351 files; TypeScript and changed browser-test ESLint. Four English/German local reviewed/incident/resume browser journeys passed. A real hosted isolation/vector explanation and transcript-resume journey passed with no-quiz and no-protocol-JSON assertions; complete saved answers were inspected. Citation repair remained active. No overall latency improvement is claimed from this single live run.


## Flat tutor response recovery

The hosted adapter also recognizes a whole serialized TutorTurn inside the text field. Recovery requires exactly the complete metadata field set plus text, successful metadata validation, and equality with the outer response metadata. The complete prose is preserved; conflicting metadata is rejected. Ordinary JSON examples remain unchanged. This extends transport recovery, not factual acceptance or question-guard exceptions.

A captured failing response was replayed successfully without generation. Matching and conflicting flat-envelope regression tests pass; all 319 scoped backend tests pass. A fresh hosted provider-setup, explanation, no-quiz and full-transcript-resume browser journey passed, with saved answers inspected. Existing question repair still occurs; no general latency improvement is claimed.
