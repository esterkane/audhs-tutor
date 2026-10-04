# Mobile navigation

2026-10-04. Narrow navigation previously displaced the workspace. Added a collapsed Menu control showing the current page, aria-expanded/controls, explicit Close menu, Escape focus return and route-key reset. Desktop keeps the same navigation DOM visible. Existing URLs, sessions and tutor state are unchanged.

Verified so far: three updated shell orientation cases and existing preferences/parking cases pass; four shell unit tests and production build passed before the final focus repair. Dedicated mobile test reproduced CSS blur before media change and now passes after tracking last navigation focus. Screenshot inspected: closed menu leaves lesson-draft content visible at 390px.

Final original checks: 24 combined browser cases, four shell unit tests, lint/types and build passed after focus repair. Existing bundle/worker warnings remain. Sanitized checkout also passed the same 24 browser cases; publication guard passed. Both repositories remain private. Keep inherited acquisition changes separate. Full bottom-navigation composition, persistent tutor and reduced header are still open; this disclosure is a bounded step, not completed mobile design.
