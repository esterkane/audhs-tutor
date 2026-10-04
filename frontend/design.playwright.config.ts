import { defineConfig } from '@playwright/test'

// Static local fixtures: no backend, database, hosted service or production route.
export default defineConfig({
  testDir: './e2e', testMatch: 'design-directions.spec.ts', workers: 1,
  use: { reducedMotion: 'reduce', screenshot: 'only-on-failure' },
  outputDir: 'test-results-design',
})
