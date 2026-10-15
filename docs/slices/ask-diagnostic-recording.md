# Ask diagnostic failure recording

The synthetic local Ask diagnostic previously wrote a case only after the responder
returned successfully. If downstream validation rejected a provider output, the
report lost the proposal needed to distinguish model failure from transport or
binding failure.

The diagnostic gateway now captures the returned ProviderResult in memory, excluding
its raw transport payload. The runner writes completed and failed cases in a finally
block before propagating the original failure. It does not retry or proceed to later
cases after failure. Per-case offsets prevent a failure before inference from being
paired with a previous case's packet or output. Existing successful reply fields
remain, with explicit outcome and provider-response fields added.

This is diagnostic tooling only. It changes no tutor prompt, routing, source access,
assessment decision or learning schedule. Captured model text is untrusted evidence,
not a correctness verdict. Reports are synthetic and local; publication policy still
applies to any raw artifacts. In-memory capture alone is not durable; callers other
than this runner must persist their own failure records. Abrupt process termination
and failures during fixture setup remain outside this change's recording guarantee.

Verification: four offline tests cover candidate packet isolation, exclusion of raw
transport, preservation of rejected structured output, successful prior cases,
rejection before inference, no stale packet attribution, no retries and disposal of
the temporary world. Targeted Ruff and bounded code review pass. No model inference
or application/browser rerun was needed for this tooling-only change.
