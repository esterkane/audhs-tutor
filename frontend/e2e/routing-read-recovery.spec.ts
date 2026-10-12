import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Routing failure preserves learner control ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let fail = true
  let hold = false
  let release!: () => void
  let calls = 0
  const pending = new Promise<void>(resolve => { release = resolve })
  const writes: string[] = []
  page.on('request', req => { if (req.url().includes('/api/models') && req.method() !== 'GET') writes.push(req.url()) })
  await page.route('**/api/models/routing', async route => {
    calls++
    if (hold) await pending
    await route.fulfill(fail ? { status: 503, json: {} } : { json: { profile: 'local-test', routes: [{ task: 'chat', override: null, chain: [{ registry_id: 'local-example', status: 'ready' }], resolved: 'local-example', problem: null, action: null }] } })
  })
  await page.goto('/models')
  const disclosure = page.locator('summary').filter({ hasText: 'Routing: which model does each task use' })
  await disclosure.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Could not load model routing.', { exact: true })).toBeVisible()
  const retry = page.getByRole('button', { name: 'Retry loading model routing', exact: true })
  await retry.focus()
  hold = true
  const before = calls
  await page.keyboard.press('Enter')
  await expect.poll(() => calls).toBe(before + 1)
  await expect(retry).toHaveAttribute('aria-disabled', 'true')
  await expect(retry).toBeFocused()
  await page.keyboard.press('Enter')
  expect(calls).toBe(before + 1)
  if (width === 320) await disclosure.focus()
  fail = false
  release()
  await expect(page.getByRole('table', { name: 'Routing profile "local-test": which model each task uses' })).toBeVisible()
  if (width === 320) await expect(disclosure).toBeFocused()
  else await expect(page.getByRole('region', { name: 'Model routing', exact: true })).toBeFocused()
  await page.getByRole('link', { name: 'Home', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Models', exact: true })).toHaveCount(0)
  fail = true
  await page.goBack()
  await disclosure.click()
  await expect(page.getByText('Could not refresh model routing. Showing the last loaded data.', { exact: true })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Routing profile "local-test": which model each task uses' })).toBeVisible()
  expect(writes).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('region', { name: 'Model routing', exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('routing-recovery.png') })
})
