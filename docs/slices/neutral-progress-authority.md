# Neutral discussion progress authority

Neutral project discussion explains research findings without assessing mastery (ADR 0025).
The imported tutor previously offered `ledger_update` in this mode and could write an invented
score and review schedule. A reproduced tool-loop test demonstrated that write before the guard.

## Host boundary

A request-local scope removes the ledger tool from neutral model requests and rejects direct
handler calls even if a client bypasses that filter. Neutral structured replies require an empty
`ledger_delta`. The final parsed turn is checked before the router can persist it. Other modes
retain their existing behavior. Existing assessments and raw histories are never rewritten.

The pinned router handles SDK status exceptions inside its SSE iterator. The host adapter maps
known `AppError` failures to that existing error channel, retaining the original cause and safe
status/message. Unexpected exceptions propagate. This avoids invoking HTTP exception handlers
after streaming has started and does not manufacture a successful final event.

## Verification

- 333 scoped Supabase/evidence tests passed, including the stream-boundary tests.
- Twelve focused authority tests passed, including direct-handler denial, other modes,
  local/hosted schemas, task-local scope and unchanged rejected text/history.
- Strict mypy passed for 349 application files; Ruff, frontend TypeScript and changed-test ESLint passed.
- Seven isolated Chromium workflows passed in 35.2 seconds, with no server traceback:
  incident/authoring handoff, English/German reviewed replies and resume, English/German
  SQLSTATE reference and full history resume, and English/German injected faulty-score recovery.
- Fault tests exercise the real tool loop and persistence boundary with a synthetic client.
  They establish authority/recovery, not actual model factual accuracy or generation speed.

- The separate upload → authored lesson → reading → notes → feedback → resume browser flow passed
  (20.4 seconds overall), using a fresh isolated database.

Broader local causal-answer accuracy and whole-request context budgeting remain separate work.
