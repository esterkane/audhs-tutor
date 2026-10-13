# Ask visual explanation controls

A learner opens an optional visual panel on a saved Ask answer, explicitly generates
locally, stops work, and reopens the saved diagram without replacing the explanation
or follow-up form. No learning objectives, assessments, scheduling or preferences
change. The diagram is a model draft, not fact-checked content or learning evidence.

## Before and implementation

Inspected the live Ask page (no generation triggered) and saved-answer component:
Ask navigation exists, but the saved-answer actions had no visual-generation consumer.
Added one disclosure in that card; history loads only when opened. Start resolves the
exact source binding before posting. Existing retry storage preserves the original
binding and key across reload; lost-response recovery is explicit, never automatic.
Status polls only while a request is active and stops on read failure. Stop persists
server cancellation; stopping the HTTP wait alone is explicitly distinguished.

The existing React Flow renderer is lazy, with plain-text explanation and complete
concept/relationship disclosure outside its error boundary. Reopening saved versions
never calls generation. Original answer/source access and follow-up are unchanged.
Source-free output stays labelled ungrounded; changed/unavailable grounding is warned.
All styles use existing tokens/primitives. No dependencies added.

## Remaining scope

Exact-version presentation-review/edit/archive controls remain a later G4 slice.
This panel lists the most recent 20 requests for the answer; older visual documents
remain stored and available through the history API. No video or assessment added.
Local-model semantic quality and owner comprehension are still unverified; mocked
browser fixtures and schema validation do not establish teaching correctness.

## Verification
661 frontend tests pass; make lint/types and production build pass (existing large
bundle warning remains). Seven sandbox browser journeys pass: Ask at390/1280,
lost start response/same-key retry and stop/reload, renderer failure, history error,
and both existing visual-learning flows. Keyboard disclosure/generation/concept
selection, axe, reduced motion, dark200% root-text resize and node containment pass.
Screenshots inspected at normal and enlarged text. This is root-text scaling, not
native browser zoom or screen-reader certification. Backend unchanged from1553 tests.

Visual QA fixed two issues: narrow two-column labels were too small, and resizing
within the same column layout retained a stale viewport. Diagrams now choose columns
by observed width and refit on width change; long layouts have a focusable bounded
scroll region. Final screenshots show intact labels/edges. Required code/pedagogy
review cleared initial and responsive deltas; no remaining blockers/majors. Generated
content semantic correctness and large complex graph usability remain unverified.
