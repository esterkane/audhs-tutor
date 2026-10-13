# Private lesson preview and creation API

GET /api/lesson-promotions/answers/{answer_id}/preview exposes only the owned binding,
issues, grounding category and publication_available=false. No raw history is returned.
POST /api/lesson-promotions/drafts streams at most 65536 bytes before parsing and
requires Idempotency-Key. It delegates to the existing atomic private draft command.
Missing/foreign answers share a 404; stale binding and changed-key content conflict;
invalid command errors never echo private inputs. Neither endpoint invokes a model.
The creation receipt is historical; read the draft separately for current edited state.
Local single-owner transport is not multi-user authentication.

Nine focused route/command checks pass: preview is read-only, replay/conflict,
private publication denial, missing/foreign/stale target, invalid input and dishonest
Content-Length. 1575 full backend tests, generated types/lint and bounded review pass. No UI changes;
next expose an explicit structured authoring form and recoverable same-command retry.
