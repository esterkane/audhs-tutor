---
paths:
  - "frontend/**"
---
# Frontend rules (React / TypeScript / Vite)

Layout: `frontend/src/{app,routes,features/<feature>/{components,hooks,api},components/ui,lib,stores,styles}`.
- Server state via TanStack Query (`features/<x>/api.ts` exports typed query/mutation hooks). UI/session state (state mode, energy, sensory prefs) via Zustand `stores/`.
- API types are generated from the backend OpenAPI schema (`pnpm gen:api`); never hand-write response types.
- shadcn/ui + Radix components live in `components/ui`; strengthen focus rings (3:1 non-text contrast). All interactive elements keyboard-reachable; test with `@testing-library` + `axe`.
- AuDHD UX invariants are code, not vibes:
  - One primary task per screen. No autoplay, no motion unless `prefers-reduced-motion` allows and the sensory setting is on.
  - `ParkingLotButton` is mounted in the app shell, always visible.
  - `ModeProvider` exposes `{mode, energy}`; components read density/session-length from it. Never mutate mode without user action.
  - Every adaptation the UI applies goes through `useAdaptationLog()` so it is explained and undoable.
  - Timers are soft (wind-down prompt), never hard cut-offs.
- Streaming: SSE for tutor tokens (`useTutorStream`), WebSocket for voice (`useVoiceLoop`). Render markdown with KaTeX + code highlighting; Mermaid for the skill map.
- Tests: `vitest` + Testing Library for components/hooks. Playwright smoke tests for the 3 core flows (session, review, voice) once they exist.
- Lint: eslint (typescript-eslint, jsx-a11y) + prettier. `tsc --noEmit` must pass.
