# Challenge question controls

Challenges reuse the explicit exclusion/restore controls. Acknowledged changes block submission until the learner restores and explicitly refreshes the same question. Refresh preserves the answer and uses the existing bounded-read helper. Changing mode or unmounting cancels refresh; both refreshed content and late action acknowledgements must still match the displayed question.

Typed answers use the existing session-tab draft helper, keyed by session and assessment, and are recovered when the same challenge is opened again. Successful grading/reconciled completed submission clears that draft; exclusion does not. Storage denial retains the helper's page-memory fallback, not a guaranteed reload copy. Start errors keep the draft and expose exclusion management; duplicate start clicks are guarded. No grading, mastery, scheduling or model-policy change.

## Evidence

Missing controls reproduced before implementation. Eight focused component tests pass, including failed refresh, exclusion/restore, retained answer across remount, fresh submission version, and late refresh after another mode/new answer. A required review found the stale-refresh overwrite and it was fixed with cancellation plus displayed-identity checks; follow-up review clear.

Two isolated desktop1280/narrow390 browser journeys cover keyboard controls/focus, retained answer/reload, real sandbox question-state mutations, and no horizontal overflow. Generation entry is a fixture; refreshed assessment content and exclusion/restore are real sandbox endpoints. No model generation or live DB mutation is needed. Screenshots inspected; frontend lint/types/build checked. Existing production bundle-size warning remains. Owner comprehension/screen-reader acceptance is not claimed.

## Discovered backend prerequisite

The unmocked browser start failed with `no_model_ready` for embedding even though a synthetic saved challenge existed. `api/challenge.py` eagerly resolves `Repo`; `api/deps.py:get_repo` initializes retrieval before `challenge.start` can reuse existing content. Follow-up: defer retrieval initialization until generation is actually needed, retaining learner eligibility, canonical content version and existing generation safeguards. Add an endpoint regression with an available saved challenge and no ready embedder. This is not fixed or claimed by this UI slice; the browser generation fixture must not be mistaken for end-to-end offline-start acceptance.

Linked code explain-back and listening controls, broader correction/replacement and stronger durable draft recovery remain open.

Update: the eager-retrieval limitation is resolved in challenge-cached-start.md; the browser now uses the real start endpoint with no generation-entry fixture.
