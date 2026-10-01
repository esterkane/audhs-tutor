import { defineConfig, devices } from '@playwright/test'

/**
 * Browser journeys (ADR-0013) against the disposable sandbox stack: `make sandbox-backend` seeds a
 * fresh `data/sandbox.db` (never `data/dev.db`) and serves the API with hosted providers off (empty
 * API key, daily budget 0); `make sandbox-frontend` runs Vite against it. Both are started here,
 * each waited for on its own URL, and never reused: a sandbox that is already running holds state
 * from someone's walk-through, so Playwright fails fast on a busy port instead of running on it. Vite runs directly under Node;
 * both servers receive bounded graceful shutdown.
 * Tests share that one database, so they run serially and each ends the session it started.
 * No paid provider, no microphone, no model pull. 127.0.0.1 avoids IPv6-first `localhost` flakes.
 */
export const API_PORT = process.env.SANDBOX_API_PORT ?? '8010'
export const UI_PORT = process.env.SANDBOX_UI_PORT ?? '5174'
export const API_URL = `http://127.0.0.1:${API_PORT}`
export const UI_URL = `http://127.0.0.1:${UI_PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  use: {
    baseURL: UI_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    reducedMotion: 'reduce',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'make -C .. sandbox-backend',
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
      url: `${API_URL}/api/health`,
      reuseExistingServer: false,
      timeout: 180_000,
      stdout: process.env.CI ? 'pipe' : 'ignore',
      stderr: 'pipe',
      env: { SANDBOX_API_PORT: API_PORT },
    },
    {
      // Run Vite directly so package-manager descendants cannot retain output pipes on Linux.
      command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${UI_PORT} --strictPort`,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
      url: UI_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'ignore',
      stderr: 'pipe',
      env: { API_PORT, AUDHS_VITE_CACHE_DIR: 'node_modules/.vite-browser-tests' },
    },
  ],
})
