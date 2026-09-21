---
paths:
  - "frontend/**"
---
# Frontend rules (React / TypeScript / Vite)

Layout: `frontend/src/{app,routes,features/<feature>/{components,hooks,api},components/ui,lib,stores,styles}`.
- Server state via TanStack Query (`features/<x>/api.ts` exports typed query/mutation hooks). UI/session state (state mode, energy, sensory prefs) via Zustand `stores/`.
- API types are generated from the backend OpenAPI schema with `make gen-api` (exports `backend/openapi.json`, then `pnpm gen:api`); never hand-write response types.
- shadcn/ui + Radix components live in `components/ui`; strengthen focus rings (3:1 non-text contrast). All interactive elements keyboard-reachable; test with `@testing-library` + `axe`.
- AuDHD UX invariants are code, not vibes:
  - One primary task per screen. No autoplay, no motion unless `prefers-reduced-motion` allows and the sensory setting is on.
  - `ParkingLotButton` is mounted in the app shell, always visible.
  - The Zustand store `useMode` (`stores/mode.ts`) exposes `{mode, energy, setMode, …}`; components read density/session-length from it. Never mutate mode without user action. (Older text said `ModeProvider`; there is no such component.)
  - Every adaptation the UI applies goes through `useAdaptationLog()` so it is explained and undoable.
  - Timers are soft (wind-down prompt), never hard cut-offs.
- Streaming: SSE for tutor tokens (`useTutorStream`, exists); WebSocket for voice (`features/voice/useVoiceLoop.ts`, P9: connects and records only on a click, playback stoppable, typed fallback always present). Render markdown with KaTeX + code highlighting; Mermaid for the skill map.
- Tests: `vitest` + Testing Library + `vitest-axe` for components/hooks. Browser journey tests are wanted (P1/P5) but Playwright is **not** an approved dependency yet — record the decision before adding it.
- Lint: eslint (typescript-eslint, jsx-a11y) + prettier. `tsc --noEmit` must pass.
