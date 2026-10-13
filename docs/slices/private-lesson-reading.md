# Saved private lesson reading

Show the saved explanation/worked examples for an activated answer-derived lesson before offering generation. Read-only owned content, current object ID/version/content digest, activation and original draft/answer references. No model invocation, learning evidence, new library or schema migration. Shared lessons retain existing behavior.

The existing LessonReader provides section notes and opt-in local audio. Saved content is not factual verification or task/rubric review. Generated replies remain separate; saved reading remains reachable. Failed reads expose retry, never silently claim there is no saved material. Private foreign IDs remain404. Test no generation, reload/notes, explanation→question→feedback and return, and owner isolation.

## Implemented
- GET /api/objects/{skill_id}/reading returns the latest owned, activation-linked learning object, content digest and origin references. Missing/foreign IDs share404; shared/unlinked content returns null. Read creates no model/evidence rows.
- Saved text renders before generation, with versioned reading notes, optional audio, origin/source links and honest verification caveats. Existing Let me try is immediately available; generating another explanation remains explicit. Loaded content survives refresh failure. Generated content collapses the saved reader, which remains reachable.
- Source membership is preserved, not fact-checked by this endpoint. Reading uses current saved object text; edits change its digest even when a producer retains the object version. Newer unlinked objects do not silently fall back to older activation text.

## Acceptance
Focused API tests cover exact text/identity, edit invalidation, latest-object handling, owner isolation and no model/evidence writes. Four browser journeys pass (private real HTTP/storage and existing generated explanation at390/1280). Private journey exercises draft form, activation, explicit selected session, reading, section notes/reload, abstention answer check and return with zero tutor generation requests. Teaching-block entry uses the plan API; movement choices have separate coverage. Synthetic content only; no paid calls.

686 frontend tests pass. Initial Session fixtures returned generic empty objects for unknown routes; updated their reading response to null and waited for the read to complete. Full backend:1634 passed. Sanitized focused verification:11 API tests and13 component/Session tests passed. Lint/types/build pass (existing chunk-size warning). Axe, keyboard, narrow/desktop and dark200% font checks pass; screenshots inspected. Native browser zoom and human/physical audio acceptance remain separate.

## Review fixes
Code and pedagogy reviews report no remaining blocker/major. Browser caught missing h2 before reader sections; added heading. Visual inspection caught stale “No explanation prepared” copy; suppressed when saved reading exists. A proposed newline issue was rechecked against exact bytes and browser sections and retracted.

## Remaining
This supports activated answer-derived lessons; broader authored/imported content reuse is separate. The checked answer was explicit abstention, not evidence of substantive grader quality. Saved text is not independently verified and does not qualify a task/rubric. Human clarity, actual headphones and semantic source quality remain open.
