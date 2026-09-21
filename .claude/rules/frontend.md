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
- Code editing: `features/code/CodeEditor.tsx` (CodeMirror 6 + plain textarea switch/fallback; Esc then Tab must always leave the editor). Only the four declared `@codemirror/*` packages may be imported (pnpm is strict: transitive packages do not resolve).
- Streaming: SSE for tutor tokens (`useTutorStream`, exists); WebSocket for voice (`features/voice/useVoiceLoop.ts`, P9: connects and records only on a click, playback stoppable, typed fallback always present). Render markdown with KaTeX + code highlighting; Mermaid for the skill map.
- Tests: `vitest` + Testing Library + `vitest-axe` for components/hooks. Browser journeys: Playwright (approved by ADR-0013) in `frontend/e2e/*.spec.ts`, run with `make test-e2e` against the sandbox stack (`make dev-sandbox`, never `data/dev.db`); controls located by role + accessible name (`getByText` only for status copy); each journey ends its session through the API (`docs/slices/browser-journeys.md`).
- Lint: eslint (typescript-eslint, jsx-a11y) + prettier. `tsc --noEmit` must pass.
