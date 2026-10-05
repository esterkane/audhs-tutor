# Home suggestion reflow and visualizer browser gates

2026-10-05. The completed public CI run 37324111481 passed 228 browser journeys, skipped 20 and failed three. All three failures reproduced locally before the fixes (three passed/three failed in the focused baseline).

- Home at 320px with 200% text: an existing adaptation proposal forced the grid to its content minimum width. Explicit one-column minmax sizing, shrinkable cards/buttons and wrapped labels retain every eligible decision. The regression fixture now supplies the pending proposal itself instead of depending on prior shared-database tests. No adaptation/learning logic changes.
- Visualizer sound: the global Stop control already lives outside the collapsed settings for immediate access. The outdated test searched inside the disclosure. It now verifies the disclosure stays closed, Stop is visible in the header, keyboard activation silences monitoring and analysis remains active. No runtime audio change.
- Narrow preview: nested Card and preview padding put the canvas below the existing 500px gate. Removed only duplicate preview padding, retaining the Card padding and restoring preview padding in fullscreen. No controls/content removed, no type-size reduction or relaxed position assertion.

Files: AdaptationCards.tsx, Visualizer.tsx and the Home/visualizer coordination browser fixtures. No dependencies, API/schema, prompts, models or learning-state changes.

Verification: fifteen isolated browser journeys passed, including playback continuity, keyboard stop, reduced motion, fullscreen, WebGL fallback, draft retention and measured-tone lessons. Home fixture additionally checks all three eligible buttons and keyboard focus at 200% text. Narrow canvas and suggestion screenshots inspected. 59 affected unit tests passed. Frontend lint/types/build passed (existing bundle-size warning). Independent review found no actionable issues. Text resizing is not full browser-zoom or screen-reader certification; physical headphone output remains unverified. Latest-head full CI still needs to finish.
