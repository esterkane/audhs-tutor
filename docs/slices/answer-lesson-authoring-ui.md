# Private lesson authoring from a saved answer

A saved Ask answer now offers an optional, initially collapsed lesson-authoring form.
The learner supplies a title, subject, objective, explanation, worked example,
application question and rubric criteria. Saving creates an inactive private draft
through the existing owned binding/idempotent command; no inference, learning event,
assessment qualification, grading, scheduling or activation is performed.
Mode/energy remain unchanged. Native labeled controls, keyboard disclosure and
existing design tokens are used; no new dependency or autoplay.

## Recovery and navigation

- Incomplete form text survives reload in this browser tab. Existing memory fallback
  retains it during navigation if browser storage fails, with an explicit warning.
- Before POST, the exact request and key are retained. Lost-response retry reuses
  both, while later edits remain separate. Stop waiting cannot cancel a server commit.
- A confirmed creation receipt links to the saved draft; it does not claim later
  form edits have been saved. No automatic retry or regeneration occurs.
- Draft selection is URL-based, supports reload and Back/Forward, resolves the full
  owned draft list and reports unavailable targets. Leaving an editor clears only
  its parent dirty lock, preserving recoverable text.
- Answer-derived drafts disclose unavailable activation and disable that action.
  The server's promotion-record guard remains authoritative, independent of UI origin.

## Verification

671 frontend tests pass, including request-bound validation and existing storage
failure recovery. Six isolated Chromium journeys pass at 390 and 1280 pixels:
lost-response exact retry, later-edit preservation, form reload, saved-draft link,
reload/Back, inactive state, keyboard opening, axe main-region checks, no horizontal
overflow, existing authored-draft review and dirty/conflicting draft recovery.
Both form screenshots inspected. Initial browser failures were a non-focusable test
locator, textarea label lookup after reload, and an old test expecting manual reopen;
corrected tests use actual native controls and assert the new direct reopen behavior.
Frontend type checking/lint and production build pass (existing bundle-size warning).
Unchanged backend reuses the preceding 1,575-test/API/transaction evidence.

## Review and limits

Bounded code/pedagogy review completed; no remaining blockers or majors. Review found stale parent dirty state after
browser Back; cleanup and a Back/reopen/recovered-text regression were added.
The source-history binding is not fact checking or an ownership/permission upgrade.
This is manual authoring, not automatic lesson generation; prerequisite selection,
private activation ownership and the broader G5 integration remain outstanding.
The form stores one creation receipt per answer/tab; edit a saved lesson in its
review screen. Physical assistive-technology and owner usability acceptance remain
unverified. No live lesson was activated during this slice.
