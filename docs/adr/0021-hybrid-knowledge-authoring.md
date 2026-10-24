# ADR 0021 — Hybrid knowledge authoring and scheduled evidence reviews

Status: accepted for implementation; live hosted teaching qualification requires a configured key.

The owner authorized OpenAI for authoring with a $5 daily app budget. Accepted knowledge and
ordinary learning remain local. A key alone never changes study routing. This is a bounded
exception to the previous fail-closed hosted transport policy, not general external routing.

Authoring must be explicitly enabled in learner preferences. Its separate integer-cent cap uses
the existing reserve/call/reconcile accounting and the same process reservation lock. Hosted
spend, unknown billing reservations and in-flight requests count against the UTC daily cap.
Other programs using the credential are outside this app's accounting. A missing key or budget
stops hosted authoring rather than silently switching providers. Defaults remain local/off.

Server orchestration issues a request-local permit bound to model, draft version and exact
outbound messages. Only the gateway may bind its bounded structured repair packet. The adapter
also validates the permit before transmission. Receipts and private application metadata remain
local; Chat Completions is pinned to the OpenAI endpoint with store=false and no hidden retries.
The UI identifies hosted authoring and the source/writing/context it sends. A separate private
0600 credential file is excluded from Git and learner database exports; the API never returns it.

Accepted material already has a deterministic local reading path. Authoring histories remain
complete; signed matching saved replies can be reused without a model call. Retrieved personal
notes are labelled evidence, never silently accepted facts. Existing persona/language preferences
apply independently of provider; exact quotations and code are retained.

Each accepted authored draft can register 1–3 public HTTPS documentation pages and a 1–365-day
review interval. While the app runs, a bounded worker fetches due references using the existing
SSRF-protected pinned-HTTPS fetcher. Checks do not run while the machine/app is off; overdue work
resumes later. A per-review lease prevents overlapping runs. Unchanged normalized reference text
and unchanged accepted version skip inference; this is explicitly not a new factual certification.

Changed evidence produces an append-only report with hashes, fetched excerpts, exact validated
quotes and source indices. A matching quote does not prove the model's interpretation. Failure
is recorded as failure and retried on a later day. Selected snippets are bounded evidence, not an
exhaustive check of a topic or the whole web. Authoring budget and credentials also gate reviews.

Review proposals never rewrite an accepted version or learning progress. Creating an update
makes an inactive draft, preserves all research and histories, and copies its schedule for after
activation. The user reviews and activates separately. Superseded schedules stop checking the
old version. Review policies and history participate in existing learner export/wipe and backups.
