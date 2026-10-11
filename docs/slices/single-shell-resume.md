# Single shell resume entry — 2026-10-11

Complete design-system PDF p6 requires Home ResumeCard as the resume entry and
no duplicate resume controls in the header/navigation. Current code and narrow
screenshots showed both a header Resume or manage session and a Learn menu Start
or resume link; both only navigated Home.

Removed those duplicate links and Shell's now-unused saved-session-id read. Home
navigation,brand,Quick Navigation and the Home Continue card remain. Explicit Pause,
End,topic switching and contextual recovery links remain. No route,request,session
state or checkpoint behavior changed. This does not complete the48px header or five-
destination navigation migration,or remove task-specific recovery links elsewhere.

Verification:16 App/Home unit tests;8 browser journeys covering Home continuation/
explicit switching and320/390/1280 light/dark lesson keyboard controls,checkpoints
and overflow. ESLint/type/build pass; narrow light screenshot inspected. Bounded
review found no actionable issue. Store identity is explicitly preserved in tests.
No model calls or live learner writes. Owner comprehension remains open.
