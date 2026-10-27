import { defineConfig } from '@playwright/test'
import base from './playwright.config'
export default defineConfig({
  ...base,
  testDir: './focus-e2e',
  outputDir: 'focus-test-results',
  webServer: base.webServer!.map((server, index) =>
    index === 0
      ? { ...server, command: 'make -C .. SANDBOX_DB=./data/focus-sandbox.db sandbox-backend' }
      : server,
  ),
})
