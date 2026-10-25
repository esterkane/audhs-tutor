# Verified project facts — 2026-10-25

The owner approved implementation after supplying DESIGN_SYSTEM_BRIEF.md. Its discovery-only
stop text describes the original proposal; the later owner request authorizes the core changes.

- Frontend: React 19, TypeScript 6, Vite 8, Tailwind 4; shared primitives in components/ui.
- Canonical tokens: frontend/src/index.css and docs/design/source/tokens.json. Locally bundled
  Inter/Roboto Mono already exist; no Atkinson download or CanvasUI package was added.
- Backend: Python/FastAPI, SQLAlchemy/SQLite, deterministic learning kernel. No schema change
  is needed for additional validated preferences in the existing local profile preference table.
- Tests: pytest, Vitest/Testing Library/vitest-axe, Playwright/axe-core; configured Chromium.
- Pages: Home; Learn/Areas/Programs topic selection; Session lesson and assessment; Ask and
  saved Answers; Curriculum Source → Research → Write → Review; Preferences. Preserve notebook,
  source inspection, parking, saved answers and all session/assessment routes.
- Local models run through a local service, not in browser WebGPU. Browser graphics and the
  local model may contend for the same physical GPU. This slice adds no graphics workload.
- Generation state: useTutorStream, Ask and KnowledgeAuthoring have separate busy state;
  the new ephemeral generationActivity registry combines those for reminder suppression.
- Comfort: existing local backend profile preferences, not a new cloud sync service. The global
  focus choice and welcome dismissal use device-local browser storage. Reading positions/notes
  retain their existing session/content-scoped browser keys. Full server histories stay intact.
- Sources: supplied evidence is distinct from verified truth; empty retrieval must stay visible.

See docs/design/COMFORT-LEARNING-ALIGNMENT.md for delivered scope and remaining acceptance work.
