# Authored visual command API — G4

Expose explicit private save/version, exact review and reversible archive commands
through the existing local single-owner API. `Idempotency-Key` identifies retries;
responses are historical operation receipts, never current acceptance claims.
No inference, events, learning evidence, grading or scheduling changes. No screen,
mode/energy or accessibility change in this backend transport slice.

## Implementation and limits

`POST /api/authored-visuals/commands` streams at most 131072 bytes before parsing,
including requests without a Content-Length. The existing strict command union
rejects executable fields and client model-origin claims. Validation errors use a
fixed message instead of echoing private inputs. The server selects the learner;
repository transactions retain all existing ownership, trust, revision and retry
checks. No client-supplied learner ID or generation identity is accepted.

This is local single-owner access under the existing app dependency, **not**
authenticated multi-user access. A deployment/authentication boundary would require
a separate architectural change before remote exposure; this slice does not add one.

Only the write transport is connected. Bounded read/list, target preview, historical
review/source-status display and inline Ask controls remain pending. A consumer must
refetch current state before treating any retry receipt as current document state.
Do not mark G4 complete. No browser/keyboard/visual acceptance claim is made before
a UI consumer exists. No new libraries or model calls.

## Verification

Disposable API tests cover save/replay, review, archive/restore, conflicting retry,
foreign document/answer ownership, malformed payload privacy, streamed oversize and
required request identity. No model calls or learning events are produced.
Full backend and lint verification recorded below after completion.

Independent bounded code/provenance review found no blockers or majors; reviewer
confirmed the local-owner limitation and did not independently rerun tests.

Verification completed: 1502 backend tests pass (3 warnings), 6 focused API
tests pass after OpenAPI documentation update, make gen-api and make lint pass
(Ruff/format/mypy/frontend types/ESLint). Hosted CI billing blocker remains external.
