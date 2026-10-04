# Project location links

2026-10-04, bounded C3 prerequisite for contextual tool return. Reproduced: opening /programs?course=b&step=second ignores the target and shows the first project. Project selection previously existed only in component state/localStorage, so browser history could not address individual steps.

Course, step and optional view=notebook now drive the project location. Explicit selections push history; the plain route replaces itself with the resolved saved/default location. Existing query fields are preserved. Back/Forward updates the visible target and saved place. Exact-target reselection retries storage writes. Invalid linked identities retain the existing disclosed first-available fallback and do not overwrite the unavailable saved location. No external return URL is accepted or executed.

Notes and notebook drafts stay in their existing course/section/content-keyed stores. Navigation does not start a session, run code, activate content or award evidence. Pausing remains a local explicit choice. URL identity is not a source-version contract and does not make locally configured content available on another machine.

Verification:8 project component tests including storage failure, original failing direct-link browser reproduction, then5 browser journeys covering deep-link/history plus desktop/narrow orientation/notebook recovery, keyboard,200% text and wider letter spacing, axe and no session creation on navigation. Lint/types/build pass. Narrow responsive screenshot inspected. Existing bundle/runtime warnings remain; no screen-reader or owner comprehension claim.

A scoped hooks lint exception reports the result of synchronizing URL history with external browser storage; effect dependencies are resolved primitive identity/view fields, not status. No general rule disabled.

Next C3: use verified project identity for explicitly authored relevant lab links; do not infer audio relevance from course names or suggest an unrelated lab for every lesson. Persistent tutor remains C5. Full C3/design plan is not complete.
