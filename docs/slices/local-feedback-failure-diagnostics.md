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
separate from semantic review. Exact validation-failure reason codes remain a future production
provider/gateway change; this diagnostic does not infer them from exception strings.

Verification:15 diagnostic/metadata tests passed; Ruff passed. Synthetic regressions cover valid and
unavailable timing, measured success/failure/timeout, actual runtime failure accounting, setup failure
and error/metadata privacy sentinels. Code and reporting review found no blockers/majors. This does
not establish model accuracy, a latency benchmark, or completion of the local-feedback quality gate.
