# Local feedback failure diagnostics

Report version3 distinguishes missing per-attempt timing from a measured zero. Zero, negative or
missing stored latency becomes null with latency_source=unavailable; positive recorded values retain
gateway_record provenance. This does not reconstruct old failed-attempt timings.

Every diagnostic gateway request now records monotonic wall time and completed/failed_or_cancelled
outcome in a finally block. This includes retries and must not be interpreted as single-attempt latency.
Case timing includes response handling and saved-result lookup or rollback; the accounting query is
excluded. Run timing includes setup/execution up to report serialization, with final cleanup outside a
completed report. Timing scopes are exported explicitly.

Only existing allowlisted attempt/accounting fields are exported, plus timing provenance. Stored raw
errors and arbitrary metadata are excluded. Existing authored synthetic inputs and successful model
replies remain in the private diagnostic evidence; this is not a promise that reports contain no text.
No model inference or production routing change was made for this slice. Literal validation is still
separate from semantic review. Typed validation-failure codes are now available as described below; the diagnostic never infers
them from exception strings.

Verification:15 diagnostic/metadata tests passed; Ruff passed. Synthetic regressions cover valid and
unavailable timing, measured success/failure/timeout, actual runtime failure accounting, setup failure
and error/metadata privacy sentinels. Code and reporting review found no blockers/majors. This does
not establish model accuracy, a latency benchmark, or completion of the local-feedback quality gate.

## Typed reasons — 2026-10-03

Validation failures now carry an allowlisted structured_reason_code through the provider, gateway
model-call metadata and diagnostic export: invalid_json, schema_validation, quote_not_literal,
quote_duplicate, explicit_followup_forbidden, or unknown. The classifier examines typed exceptions,
the latest Instructor failed attempt and bounded/cycle-safe causes; never error message strings,
learner input or arbitrary metadata. Older/unknown metadata remains unknown.

The feedback rules, model routes, repair count and accounting are unchanged. Existing raw-error
logging is unchanged; only the new diagnostic field has this restricted content contract. A literal
quote check cannot establish whether a response is semantically correct or helpful.

Verification: 50 provider/schema/diagnostic tests plus 35 feedback/accounting tests passed (the typed
reason suite overlaps). Strict mypy passed all 186 app files; targeted Ruff and format checks passed.
The gateway regression verifies failed-attempt persistence, usage preservation, successful repair,
no failure code on the successful attempt, and exclusion of arbitrary reason strings from export.
Independent code review found no blockers or majors. A fresh local-only notebook diagnostic is
running against synthetic inputs and a disposable database; results are private and not a gate pass.
