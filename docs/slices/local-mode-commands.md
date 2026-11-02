# Local project mode commands

An entire supported mode command now receives a deterministic acknowledgement without
model generation. English and German use the existing bounded mode-command grammar.
Quoted text, code and mixed requests are not reduced to acknowledgements. Ordinary
questions retain their existing route. The selected mode is persisted through the usual
Final event and the complete command/acknowledgement exchange is appended to history.
No mastery, task completion or factual teaching claim is inferred from a mode change.

Examples: `Switch to neutral mode.` and `Bitte wechsle in den Prüfungsmodus.`.
This does not claim support for arbitrary paraphrases or a general decoding speedup.

Verification: 384 scoped backend tests passed; Ruff and targeted mypy passed. Six isolated
English/German browser journeys passed in 22.9 seconds, including mode persistence,
follow-up explanations and complete transcript preservation after reload. TypeScript
and changed-test ESLint passed. This suite made zero recorded model calls.
