# Desktop navigation rail

2026-10-04. Navigation previously competed with content across the top at desktop widths. Moved existing navigation into a 240px desktop rail on the canonical sunken surface, separate from the workspace. Normal workspace now uses the specified 896px maximum; existing wide tools retain their maximum. Header retains area/audio/capture/session controls. One DOM navigation preserves route and keyboard order. At narrow widths navigation remains wrapping in flow.

Before: three shell journeys passed. After: ten browser checks passed covering shell routes, Back/Forward, keyboard skip and focus, 320/390/1280 widths, 200% text, accessibility scan of header and navigation, Park-dialog recovery and Home resume. Four shell unit tests, lint, types and build passed. Desktop and 320px screenshots inspected. No session, tutor, learning or model-state logic changed.

Remaining: compact mobile navigation, rail collapse, shorter header, contextual tutor and mode/tool integration are still unfinished. Rail is deliberately not sticky, avoiding another independent scroll/focus region in this slice. Existing build chunk/worker warnings remain. This is a desktop composition step, not completion of C1–C7 or owner usability acceptance.
