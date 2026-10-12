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
