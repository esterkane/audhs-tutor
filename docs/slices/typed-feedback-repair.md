# Typed structured-feedback repair

The gateway now gives fixed, actionable repair instructions for three typed failures:
nonliteral learner quotations, repeated quotations, and explicit-mode follow-up questions.
Quotation repair asks for an exact contiguous passage from the current answer and separates
corrections from quotations. It distinguishes required JSON encoding from unwanted Markdown
escaping. The explicit-mode repair asks for null follow-up and no question moved to another field.

The literal-substring guard remains unchanged. Fixed guidance uses no exception-wrapper text.
Unknown/other failures retain the pre-existing sanitized generic repair path. This does not
claim that all existing error logging or unknown-wrapper handling is privacy-safe.
Retry count, provider routing, accounting, model assignment and feedback schemas are unchanged.
The diagnostic report labels structured-repair.v2 independently of the workspace prompt version.

Verification: 56 targeted provider, schema, accounting and diagnostic tests passed; the updated
gateway integration regression passed all 8 typed-reason tests. Strict mypy passed 186 app files.
Ruff and format checks passed using backend configuration. The sanitized checkout passed 41
focused tests. Independent code review found no blockers or majors.

This does not enforce semantic correctness, detect every hidden question, or guarantee successful
repair. Local synthetic results and manual review are separate evidence, never an automatic gate.

## Local result and next implementation

The completed synthetic local run still rejected all three cleaning-case attempts as nonliteral
quotations. Fixed guidance did not solve this observed failure. Keep the failure in delivery counts;
no semantic score exists for a response that was never delivered.

Next bounded experiment: create request-scoped labelled passages from the exact learner answer,
ask the model to select passage IDs, then construct the displayed learner quotation by lookup.
Keep the full answer visible as untrusted context. Never put learner text in JSON schema. Unknown
IDs, duplicate selected text and cross-request selections must fail. The public rendered feedback
contract and literal-attribution check remain; a valid selection still does not prove the judgment.
Preserve original request and selected passage provenance in saved feedback, invalidate obsolete
exact replays, test Unicode/whitespace/long answers and request isolation, and re-evaluate all cases.
This experiment is queued, not implemented or accepted as a quality improvement.
