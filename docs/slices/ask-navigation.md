# Direct Ask navigation

The owner could not find Ask. Live Home inspection showed only a Home heading link
and a Tools entry, with no direct shared shortcut. Add Ask tutor to the existing
navigation footer, alongside Tools and Preferences; keep the five primary destinations.
Native link keyboard behavior and current-page indication use existing tokens/styles.
No API, model, grading, scheduling, mode/energy or learner-state changes; no events.
Verify desktop and narrow navigation, keyboard entry/Back, text enlargement and axe.

## Verification

Three sandbox browser journeys passed at 1280/390/320px: keyboard Ask entry,
current-page state, Back, original Tools/primary routes, 200% text and axe.
Desktop and 320px Ask screenshots inspected. Full frontend 656 tests, lint,
mypy/TypeScript and build passed (existing bundle warnings). Backend unchanged;
prior 1,445-test result retained. Code/accessibility review: no blockers/majors.
Owner discoverability and assistive-technology acceptance remain unverified.
