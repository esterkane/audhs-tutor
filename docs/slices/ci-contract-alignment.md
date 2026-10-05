# CI contract alignment — 2026-10-05

The full GitHub suites exposed test drift outside the tutor streaming slice: exact table inventory omitted the existing migrated thought_action table; legacy promotion of a dropped thought expected400 although revision conflict is409; capture payload equality omitted its UUID request_key; jsdom lacks the native dialog methods used by the shell.

Updated only tests and test setup. Keep exact table and payload equality, require a UUID v4, and assert both revision_conflict and unchanged dropped state. Add test-only dialog open/close methods that model the open attribute and close event. This shim does not implement or prove browser modal focus behavior. No application code, learning logic, migration, routing or dependencies changed.

Verification: full backend847 tests and frontend516 tests pass locally; Ruff, frontend ESLint and TypeScript pass. Nine isolated Chromium journeys cover shell orientation at1280/390/320px, reminder removal/promotion/undo, stale conflict, same-receipt retry, and native quick-navigation open/filter/Escape/focus return at390/1280px. Screenshot inspected. Independent review found no weakened assertions or blockers. Existing dependency deprecation and canvas warnings remain. Production build from the unchanged application source in the preceding slice remains applicable; no claim that the dialog shim verifies accessibility.

GitHub rerun follows publication; local success is not remote CI success. Full browser suite and broader design/learning acceptance remain separate gates.
