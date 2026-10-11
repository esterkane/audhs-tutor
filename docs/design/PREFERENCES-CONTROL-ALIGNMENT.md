# Preferences control alignment

2026-10-11 — Complete Design System, Preferences controls (p12), shared target and focus requirements (pp5–8).

Boolean preferences now use a labelled native switch with explicit On/Off text, semantic palette tokens, visible keyboard focus and a full-row target of at least 44px. The confirmed server value remains visible during saving; repeated toggles are disabled until completion. Failed saves retain the confirmed value and allow retry. Notification permission remains an explicit existing action. Enum controls and learning logic are unchanged.

Verification: 9 affected Playwright journeys passed (320/1280 widths, keyboard Space, duplicate prevention, failed-save recovery, persisted reload, sections, serialized writes and stale-read recovery); 9 preference API unit tests passed; targeted ESLint and production build/type checking passed. Inspected desktop and narrow screenshots with visible focus. The 200% root-text reflow check passed; it is not a browser zoom or screen-reader test. Code and pedagogy reviews found no blockers or majors. Build retains the existing large-chunk warning.

Remaining: broader disclosure/typography adoption and assistive-technology acceptance. This bounded slice does not establish complete application design compliance.

## Segmented choices

2026-10-11 — Preferences enum choices now share a bordered sunken group, with a card surface and selection ring for the confirmed choice instead of multiple primary action fills. Existing fieldset labels, pressed state, options, effect hints, handlers and serialized writes are unchanged. The variant is opt-in; other Choice consumers are unchanged. No dependencies or learning-policy changes.

Before-change browser evidence: five existing section/save-order journeys passed; screenshot inspection confirmed repeated primary-blue selections. After-change: the same five journeys and four new light/dark, 320/1280 keyboard/selection/44px-target/200%-root-text checks passed. Nine preference API tests, targeted lint and production type/build checks passed. Desktop/light and narrow/dark screenshots inspected. Code and pedagogy reviews found no blockers or majors. Browser zoom, assistive technology and human comprehension remain separate open gates.
