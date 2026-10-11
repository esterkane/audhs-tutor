import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk } from './helpers'

for (const width of [320, 1280]) test(`Learn recovery is readable and keyboard operable ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let reads = 0
  const writes: string[] = []
  page.on('request', req => { if (req.url().includes('/api/') && req.method() === 'POST') writes.push(req.url()) })
  await page.route('**/api/sessions/current', route => {
    reads++
    return route.fulfill({ status: 503, json: { detail: 'Unavailable' } })
  })
  await page.goto('/learn')
  await expect(page.getByRole('alert')).toContainText('Could not check your saved session')
  const retry = page.getByRole('button', { name: 'Retry', exact: true })
  const initialReads = reads
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect.poll(() => reads).toBe(initialReads + 1)
  await expect(retry).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Return Home', exact: true })).toBeFocused()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('learn-recovery.png'), fullPage: true })
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/$/)
  expect(writes).toEqual([])
})

test('Learn resolves the real saved session without advancing it', async ({ page, request }) => {
  await endOpenSession(request)
  try {
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const saved = await currentSession(request)
    const writes: string[] = []
    page.on('request', req => { if (req.url().includes('/api/') && req.method() === 'POST') writes.push(req.url()) })
    await page.goto('/learn')
    await expect(page).toHaveURL(/\/session$/)
    await expect(page.getByRole('main')).toBeFocused()
    expect(await currentSession(request)).toEqual(saved)
    expect(writes).toEqual([])
    await page.reload()
    await expect(page).toHaveURL(/\/session$/)
    expect(await currentSession(request)).toEqual(saved)
  } finally { await endOpenSession(request) }
})
