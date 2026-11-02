# Project tutor mid-answer failures

A gateway refusal during a tool/repair loop previously escaped the imported SSE router after response headers had been sent. The host now converts gateway failures to its existing HostRefusal protocol with safe, provider-neutral recovery text. The router emits a terminal error event for that protocol. Failed and blocked call accounting is committed; no partial tutor turn is stored.

The browser already retains unanswered questions locally. Keep that behavior: after an error, reload preserves the previous transcript and offers restoring the pending question without automatic resend. Budget reservations, caps, retry limits and model routing are unchanged. The message mentions both availability and the shared budget because a gateway failure alone does not prove which caused it. It never exposes raw provider error text.

Validation: 390 host Supabase tests; 232 native tests with 47 service-dependent skips; Ruff, format, mypy and changed browser ESLint pass. Four isolated Chromium recovery workflows pass in 17.8 seconds. Browser failure transport is deterministic/mocked; native router and host adapter tests independently exercise the real exception mapping, unchanged history, no partial append, retained accounting and lock release. No paid inference was needed. This fixes recovery, not factual answer quality or decoding speed.
