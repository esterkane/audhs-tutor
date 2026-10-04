# Preferences page heading — Phase10 Stage1b

2026-10-04. Reproduced Preferences rendering its page title as h2 at390/1280px before production edits; both targeted heading checks failed specifically because no h1 existed. This is an orientation/semantic correction, not a claim that a missing h1 alone establishes WCAG nonconformance.

CardTitle now accepts an optional heading element (`as`, h1–h6), preserving h2 as its default and existing classes/attributes. Preferences selects h1 in loading and ready states. Adaptation log retains h2. No preference values, effects, mutations, styles or learning logic changed. Button sizing remains untouched because this slice did not establish a specific button defect.

Verification: five browser checks passed (desktop/narrow Preferences heading, keyboard setting change and Back, loading orientation, desktop/320px shell keyboard navigation). Fourteen existing Home/adaptation unit tests passed. ESLint, TypeScript and production build passed; existing bundle-size and spectrogram-worker warnings remain. Fixture settings verify exact outgoing save values; this is not a full real-service preference acceptance test. Narrow before/after images are byte-identical; desktop and narrow images inspected. Evidence in docs/design/evidence/phase10b.

Remaining: initial read failures still show loading, preference units/internal terms remain, other route headings are not migrated, full screen-reader/zoom coverage remains open. The immediate next bounded correction is Stage2a Preferences failed-read recovery, including stale-content preservation; do not mix it with a full settings redesign.
