import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) for (const detail of [false, true]) test(`saved answer read timeout and keyboard recovery ${width} detail=${detail}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  await page.addInitScript(({ detail }) => {
    const original = window.fetch
    Object.assign(window, { allowAnswerRead: false })
    window.fetch = (...args) => {
      const path = String(args[0])
      const matches = detail ? path === '/api/answers/timeout-answer' : path.startsWith('/api/answers?')
      if (!matches) return original(...args)
      if (!(window as unknown as { allowAnswerRead: boolean }).allowAnswerRead) return new Promise<Response>(() => {})
      const value = detail ? { id: 'timeout-answer', surface: 'tutor', created_at: '2026-10-01', request_text: 'Explain this idea', text: 'Recovered saved explanation.', request: {}, metadata: {} } : { items: [], next_cursor: null }
      return Promise.resolve(new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } }))
    }
  }, { detail })
  await page.goto(detail ? '/answers/timeout-answer' : '/answers?q=retained')
  await page.clock.install()
  // Start a fresh navigation after installing the clock so the read deadline is controlled.
  await page.reload()
  await expect(page.getByRole('status').filter({ hasText: detail ? 'Loading answer' : 'Loading saved answers' })).toBeVisible()
  await page.clock.fastForward(15001)
  await expect(page.getByRole('alert').filter({ hasText: 'Could not load' })).toBeVisible()
  const retry = page.getByRole('button', { name: detail ? 'Retry answer' : 'Retry history', exact: true })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(retry).toBeFocused()
  await expect(retry).toHaveAttribute('aria-disabled', 'true')
  await page.clock.fastForward(15001)
  await expect(retry).toHaveAttribute('aria-disabled', 'false')
  await expect(retry).toBeFocused()
  await page.evaluate(() => Object.assign(window, { allowAnswerRead: true }))
  await page.keyboard.press('Enter')
  await expect(page.getByText(detail ? 'Recovered saved explanation.' : /No saved answers in this view yet/)).toBeVisible()
  if (!detail) await expect(page.getByRole('searchbox', { name: 'Search saved answers' })).toHaveValue('retained')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: `/tmp/answer-read-${width}-${detail}.png`, fullPage: true })
})

for (const width of [320, 1280]) test(`saved history survives failed refresh after return ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  let fail = false
  let hold = false
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  const item = { id: 'retained-answer', request_text: 'A saved question', preview: 'Earlier explanation', surface: 'tutor', created_at: '2026-10-01' }
  await page.route('**/api/answers?*', async route => {
    if (hold) await pending
    await route.fulfill(fail ? { status: 503, json: {} } : { json: { items: [item], next_cursor: null } })
  })
  await page.route('**/api/answers/retained-answer', route => route.fulfill({ json: { ...item, text: 'Saved detail text.', request: {}, metadata: {} } }))
  await page.goto('/answers?q=saved')
  const link = page.getByRole('link', { name: 'A saved question', exact: true })
  await link.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Saved detail text.', { exact: true })).toBeVisible()
  fail = true
  await page.getByRole('link', { name: 'Back to saved answers' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert')).toContainText('Showing the last loaded answers')
  await expect(link).toBeVisible()
  await expect(page.getByRole('searchbox', { name: 'Search saved answers' })).toHaveValue('saved')
  hold = true
  const retry = page.getByRole('button', { name: 'Retry history' })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(retry).toHaveAttribute('aria-disabled', 'true')
  await expect(retry).toBeFocused()
  await expect(link).toBeVisible()
  await page.screenshot({ path: `/tmp/history-refresh-${width}.png`, fullPage: true })
  fail = false
  release()
  await expect(retry).toHaveCount(0)
  await expect(link).toBeVisible()
  fail = true
  await page.getByRole('searchbox', { name: 'Search saved answers' }).fill('different')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Could not load saved answers.')
  await expect(link).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

for (const width of [320, 1280]) test(`saved detail retains transient failures but respects unavailable records ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  let status = 200
  let hold = false
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  const item = { id: 'cached-detail', request_text: 'Cached question', preview: 'Saved content', surface: 'tutor', created_at: '2026-10-01' }
  await page.route('**/api/answers?*', route => route.fulfill({ json: { items: [item], next_cursor: null } }))
  await page.route('**/api/answers/cached-detail', async route => {
    if (hold) await pending
    await route.fulfill({ status, json: status === 200 ? { ...item, text: 'Retained explanation text.', request: {}, metadata: {} } : {} })
  })
  await page.goto('/answers/cached-detail')
  const text = page.getByText('Retained explanation text.', { exact: true })
  await expect(text).toBeVisible()
  await page.getByRole('link', { name: 'Back to saved answers' }).click()
  status = 503
  await page.getByRole('link', { name: 'Cached question', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not load this answer.' })).toContainText('Showing the last loaded answer')
  await expect(text).toBeVisible()
  await page.screenshot({ path: `/tmp/detail-refresh-${width}.png`, fullPage: true })
  status = 404
  const retry = page.getByRole('button', { name: 'Retry answer' })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert').filter({ hasText: 'This saved answer is unavailable.' })).toBeVisible()
  await expect(text).toHaveCount(0)
  hold = true
  status = 200
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(retry).toHaveAttribute('aria-disabled', 'true')
  await expect(text).toHaveCount(0)
  release()
  await expect(text).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
