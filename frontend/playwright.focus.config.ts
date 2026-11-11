import { defineConfig } from '@playwright/test'
import base from './playwright.config'
const recallDb = process.env.AUDHS_RECALL_FIXTURE_DB
if (recallDb && !/^\/tmp\/audhs-c2-browser-[\w-]+\/synthetic\.db$/.test(recallDb))
  throw new Error('Delayed recall requires a disposable browser database')
export default defineConfig({
  ...base,
  testDir: './focus-e2e',
  outputDir: 'focus-test-results',
  webServer: base.webServer!.map((server, index) =>
    index === 0
      ? { ...server, command: 'make -C .. sandbox-backend', env: { ...server.env, SANDBOX_DB: recallDb || './data/focus-sandbox.db' } }
      : server,
  ),
})
