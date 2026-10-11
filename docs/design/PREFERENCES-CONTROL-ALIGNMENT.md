# Preferences control alignment

2026-10-11 — Complete Design System, Preferences controls (p12), shared target and focus requirements (pp5–8).

Boolean preferences now use a labelled native switch with explicit On/Off text, semantic palette tokens, visible keyboard focus and a full-row target of at least 44px. The confirmed server value remains visible during saving; repeated toggles are disabled until completion. Failed saves retain the confirmed value and allow retry. Notification permission remains an explicit existing action. Enum controls and learning logic are unchanged.

Verification: 9 affected Playwright journeys passed (320/1280 widths, keyboard Space, duplicate prevention, failed-save recovery, persisted reload, sections, serialized writes and stale-read recovery); 9 preference API unit tests passed; targeted ESLint and production build/type checking passed. Inspected desktop and narrow screenshots with visible focus. The 200% root-text reflow check passed; it is not a browser zoom or screen-reader test. Code and pedagogy reviews found no blockers or majors. Build retains the existing large-chunk warning.

Remaining: enum segmented controls, broader disclosure/typography adoption, dark-theme and assistive-technology acceptance. This bounded slice does not establish complete application design compliance.
