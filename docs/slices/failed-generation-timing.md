# Failed structured-generation timing

Structured-output validation failures previously wrote zero latency to model_call even
when the provider spent time generating the rejected response. They now record elapsed
wall time from the existing per-attempt monotonic clock. Successful-call timing, token
accounting, budgets, retry limits, complete answers and saved history are unchanged.
Historical rows are not rewritten or assigned guessed timings.

A controlled regression first reproduced 0 ms for a simulated 1,250 ms failed attempt;
it now records 1,250 ms. The 55 focused provider, accounting and attempt-boundary tests,
Ruff, formatting and targeted mypy pass. An isolated hosted browser workflow passed in
27.8 seconds, including setup-error recovery, two technical explanations and full resume.
That live run did not reproduce a format failure; failed-attempt coverage is deterministic.
This corrects latency measurement, not generation speed itself.
