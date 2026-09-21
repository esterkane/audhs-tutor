import { existsSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, reachLearnBlock, skillIdBySlug } from './helpers'

/**
 * The code exercise runs from this app's own origin only (ADR-0013): every request to another host
 * is aborted by the browser context, the pinned runtime is fetched from `/pyodide/`, and the starter
 * code still executes and reports its checks. Skipped — loudly — when `make pyodide` has not been
 * run on this machine, so a missing runtime is never mistaken for a passing test.
 */
const runtimeInstalled = existsSync(new URL('../public/pyodide/pyodide.js', import.meta.url))

test.skip(!runtimeInstalled, 'Pyodide runtime not installed here: run `make pyodide` first')

test.beforeEach(async ({ request }) => endOpenSession(request))
test.afterEach(async ({ request }) => endOpenSession(request))

test('the starter code runs with every external host blocked', async ({ page, request, context }) => {
  test.setTimeout(120_000)
  const external: string[] = []
  await context.route('**/*', (route) => {
    const host = new URL(route.request().url()).hostname
    if (host === '127.0.0.1' || host === 'localhost') return route.continue()
    external.push(route.request().url())
    return route.abort()
  })
  const runtime: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/pyodide/')) runtime.push(new URL(r.url()).pathname)
  })

  await reachLearnBlock(page)
  const session = await currentSession(request)
  const moved = await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, {
    data: { skill_id: await skillIdBySlug(request, 'attn-scaled') },
  })
  await expectOk(moved)
  await page.reload()
  await page.getByText(/^Code exercise \(optional/).click()
  await expect(page.getByText(/served by this app from its own origin/)).toBeAttached()

  await page.getByRole('button', { name: 'Run' }).click()
  const checks = page.getByRole('list', { name: 'Checks' })
  await expect(checks).toBeVisible({ timeout: 90_000 })
  await expect(checks.getByText('failed:')).toHaveCount(3) // the starter returns None everywhere
  await expect(page.getByText(/Ran in \d+ ms in your browser/)).toBeVisible()

  expect(external, 'no request may leave the app origin').toEqual([])
  expect(
    runtime.some((p) => p.endsWith('/pyodide/pyodide.asm.wasm')),
    runtime.join('\n'),
  ).toBe(true)
  expect(
    runtime.some((p) => p.includes('numpy-')),
    runtime.join('\n'),
  ).toBe(true)
})

test('a missing runtime is an explicit error, and nothing reaches a CDN', async ({
  page,
  request,
  context,
}) => {
  const external: string[] = []
  await context.route('**/*', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/pyodide/pyodide.js')) return route.abort() // "not installed"
    if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') return route.continue()
    external.push(url.href)
    return route.abort()
  })
  await reachLearnBlock(page)
  const session = await currentSession(request)
  const moved = await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, {
    data: { skill_id: await skillIdBySlug(request, 'attn-scaled') },
  })
  await expectOk(moved)
  await page.reload()
  await page.getByText(/^Code exercise \(optional/).click()
  await page.getByRole('button', { name: 'Run' }).click()
  const alert = page.getByRole('alert')
  await expect(alert).toContainText('The Python runtime is not installed in this app', { timeout: 30_000 })
  await expect(alert).toContainText('make pyodide')
  await expect(page.getByRole('button', { name: 'Try loading the runtime again' })).toBeVisible()
  expect(external).toEqual([])
})

test('a runtime of another version is refused after loading', async ({ page, request, context }) => {
  await context.route('**/pyodide/pyodide.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: 'self.loadPyodide = async () => ({ version: "0.0.0" })',
    }),
  )
  await reachLearnBlock(page)
  const session = await currentSession(request)
  await expectOk(
    await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, {
      data: { skill_id: await skillIdBySlug(request, 'attn-scaled') },
    }),
  )
  await page.reload()
  await page.getByText(/^Code exercise \(optional/).click()
  await page.getByRole('button', { name: 'Run' }).click()
  await expect(page.getByRole('alert')).toContainText('Installed Python runtime is 0.0.0, expected 0.27.8', {
    timeout: 30_000,
  })
})
