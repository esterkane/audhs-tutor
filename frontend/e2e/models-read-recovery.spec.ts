import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Models read failure can be retried with keyboard ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let fail = true
  let calls = 0
  let release!: () => void
  let hold = false
  const pending = new Promise<void>(resolve => { release = resolve })
  const writes: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/models') && request.method() !== 'GET') writes.push(request.url())
  })
  await page.route('**/api/models', async route => {
    calls++
    if (hold) await pending
    await route.fulfill(fail ? { status: 503, json: {} } : { json: { models: [] } })
  })
  await page.goto('/models')
  await expect(page.getByText('Could not load models.', { exact: true })).toBeVisible()
  const retry = page.getByRole('button', { name: 'Retry loading models', exact: true })
  await retry.focus()
  const before = calls
  hold = true
  await page.keyboard.press('Enter')
  await expect.poll(() => calls).toBe(before + 1)
  await expect(retry).toBeFocused()
  await expect(retry).toHaveAttribute('aria-disabled', 'true')
  await page.keyboard.press('Enter')
  expect(calls).toBe(before + 1)
  if (width === 320) { await page.keyboard.press('Tab'); await expect(retry).not.toBeFocused() }
  const focusBeforeResponse = await page.evaluate(() => { document.activeElement?.setAttribute('data-recovery-focus', 'true'); return document.activeElement?.tagName })
  fail = false
  release()
  await expect(page.getByText('No models registered.', { exact: true })).toBeVisible()
  await expect(page.getByText('Could not load models.', { exact: true })).toHaveCount(0)
  if (width === 320) { expect(focusBeforeResponse).toBeTruthy(); await expect(page.locator('[data-recovery-focus=true]')).toBeFocused() }
  else await expect(page.getByRole('region', { name: 'Model registry', exact: true })).toBeFocused()
  expect(writes).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('models-recovered.png'), fullPage: true })
})

for (const width of [320, 1280]) test(`Models retains cached registry when refresh fails ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  let fail = false
  await page.route('**/api/models', route => route.fulfill(fail ? { status: 503, json: {} } : { json: { models: [{ id: 'example', display_name: 'Example local model', runtime: 'ollama', role: 'chat', status: 'available', benchmark: null }] } }))
  await page.goto('/models')
  await expect(page.getByText('Example local model', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Home', exact: true }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { name: 'Models', exact: true })).toHaveCount(0)
  fail = true
  await page.goBack()
  await expect(page.getByText('Could not refresh models. Showing the last loaded data.', { exact: true })).toBeVisible()
  await expect(page.getByText('Example local model', { exact: true })).toBeVisible()
  const retry = page.getByRole('button', { name: 'Retry loading models', exact: true })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(retry).toHaveAttribute('aria-disabled', 'false')
  await expect(retry).toBeFocused()
  await expect(page.getByText('Example local model', { exact: true })).toBeVisible()
})
