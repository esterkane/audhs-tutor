# Visual attempt admission and atomic publication — G4

Connect durable request primitives to two required worker boundaries: provider attempt
admission and atomic result saving. This slice does not yet start inference, expose
start/status/cancel APIs or add UI. No learning, grading, scheduling or routing change.

## Boundaries

ModelGateway.complete accepts an optional asynchronous before_attempt hook. It runs
after transport validation and before budget reservation, on every structured repair
and fallback. Rejection propagates immediately without invoking the provider or
opening a budget reservation. Existing callers retain their behavior. This is an
admission budget: a later budget rejection may consume a slot without a provider call;
it never grants extra attempts. The future visual worker must supply the durable gate.
Streaming calls are unchanged and are not the planned graph-generation transport.

GenerationRequests.complete uses one short writer transaction. It verifies active
worker authority and a consumed attempt, exact bound intent, owned successful local
FORMAT call, generation/binding/prompt metadata, target/source currency and trust,
and bounded non-executable content. It invokes the existing version writer inside
that same transaction, stores model/prompt origin from the call and marks the request
completed with its version ID. Concurrent completion returns the stored result.
Cancel/restart prevents publication; cancellation after completion leaves the result.
A transaction failure rolls back both visual history and request completion.

This is a trusted-worker API, not a client model-origin override. Matching call
metadata is provenance, not proof the graph is factually correct. Review and source
permission policies remain unchanged. The model-call rows retain generation_id so
attempts can be traced without adding raw prompts to request records.

## Verification and remaining work

Tests use synthetic records and fake providers only: cancel-before-call, bounded
repairs/fallbacks, duplicate completion, stale worker, changed answer, foreign/hosted
or mismatched call, cancel/save race and failure after visual flush. Existing usage
accounting tests remain green. No paid or live model call, no migration or live wipe.

Next implement the actual local graph worker and prompt/schema: resolve bounded
context, reserve/claim, invoke complete with the durable gate, save via this atomic
path and handle failure/cancellation. Then start/status/cancel routes and inline Ask
controls with real browser and conceptual-quality gates. Stopping an in-flight
provider task remains worker integration work. Do not mark G4 complete.

Final verification: 1535 backend tests pass (3 warnings), including new race and
foreign/hosted-call cases; prior focused gateway/accounting run passed37 tests.
Ruff/format/mypy/frontend types/ESLint pass. Bounded code/provenance review found no
blockers or majors, limited to these boundaries; reviewer did not rerun tests.
Private snapshot verified unchanged. Hosted CI billing remains external; no hosted
pass claimed. No new UI consumer, so browser acceptance remains open.
