# Study tutor choices — UX26-04 / Q2 / R7

Story: a learner opens contextual help and can ask for an explanation, a hint or type a follow-up
without first interpreting a menu of teaching modes. Optional guided questioning has an explicit
entry, visible current approach and reachable return to explanation. Existing prompts, model routing,
request identities, saved answers and ownership remain unchanged.

Reproduced in the live read-only Programs help panel: four equally prominent actions (including a
disabled review with no answer), full provider paragraph and reuse checkbox precede the message box.
Implementation: prioritize explanation/hint; hide irrelevant review action when there is no work;
collapse optional guided-question and saved-reuse settings while keeping data/provider disclosure
visible. Preserve original accessible action names and all follow-up/recovery controls. Fix undefined
surface/border utilities only on the touched tutor. Mode/energy/audio defaults unchanged.

Acceptance: opening help never invokes a model; guided questions require explicit selection;
answer-to-question → feedback → follow-up stays in one conversation; Explain instead remains directly
available; review-only answer checking/provider disclosure remains visible; saved reuse is inspectable;
keyboard focus and notes survive notebook round trip. Verify actual narrow/desktop flows and recovery.

## Verification — 2026-10-03

Failing behavioral test reproduced the competing/irrelevant review action before implementation.
Full frontend310 (80 files), focused26, nine isolated browser journeys passed. Journeys cover desktop/
narrow notebook-focused guided questions and follow-up, answer feedback, lost-response remount and
denied storage. Existing native notebook action was updated to the new explicit tools/reader navigation
in its journey. Live help panel inspected without sending a model request. Production build passed
with existing large-bundle warning. ESLint rerun after Playwright finished (initial parallel run raced
Playwright's test-results cleanup). Both code and pedagogy reviews cleared.

No model/prompt/API or learning-state change. No paid model calls. Owner comprehension still open.
Next: UX26-05 navigation/current-page/status, then audio and shared component consistency.
