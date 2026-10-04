# Authoritative palette adoption

2026-10-04. Existing semantic colors diverged from the owner-supplied design system. Adopted its twelve existing light/dark roles, including separate focus-ring color, and its 2px offset focus outline. Explicit and system themes agree. Only shared CSS and its browser assertions changed; learning logic, model routing, typography and layout are unchanged.

Verification: eight baseline browser cases passed; eight updated cases passed across light/dark/system modes at 390/1280px. The narrow cases include large text and reduced motion. Assertions cover exact canonical values, contrast, keyboard focus/input, no horizontal overflow and retained draft after pause/resume. Lint, TypeScript and production build passed. Existing large-chunk and spectrogram worker warnings remain.

Visually inspected light desktop and dark narrow lesson captures in ../ux/evidence/design-palette. Dark input boundary contrast 4.17:1, focus 5.79:1, inline code 13.56:1. No clipped text or focus was observed in those captures. This is not a full contrast audit of every component.

Remaining: uploaded typography, component primitives, desktop rail/mobile shell and contextual tutor are not implemented by this palette change. Repeated audio disclosures and long stacked lesson sections remain visible; address them in the approved workspace sequence. Physical audio and owner comprehension remain unverified.
