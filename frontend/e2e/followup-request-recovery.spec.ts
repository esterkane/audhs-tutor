import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`follow-up retry preserves parent and new draft after reload (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'session' } }))
    await page.route('**/api/answers/*/feedback', (route) =>
      route.fulfill({ json: { verdict: null, note: '', hidden: false, revision: 0 } }),
    )
    await page.route('**/api/answers/parent', (route) =>
      route.fulfill({
        json: {
          id: 'parent',
          text: 'Compare group representation.',
          request_text: 'Why compare?',
          request: {},
          metadata: {},
          created_at: '2026-10-01T10:00:00Z',
        },
      }),
    )
    let key = ''
    let generations = 0
    await page.route('**/api/answers/parent/followup/stream', async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        session_id: 'session',
        question: 'Show a small example.',
        purpose: 'followup',
      })
      const nextKey = route.request().headers()['idempotency-key']
      expect(nextKey).toMatch(/^[a-f0-9-]{36}$/)
      if (!key) {
        key = nextKey
        generations++
        await route.abort('failed')
      } else {
        expect(nextKey).toBe(key)
        await route.fulfill({
          contentType: 'text/event-stream',
          body: `event: done\ndata: ${JSON.stringify({
            text: 'Illustrative: compare 9/10 with 6/10.',
            answer_id: 'child',
            turn_id: 'turn',
            model: 'fixture',
            route: 'fake',
          })}\n\n`,
        })
      }
    })
    await page.goto('/answers/parent')
    const input = page.getByRole('textbox', { name: 'Your follow-up question' })
    await input.fill('Show a small example.')
    await page.getByRole('button', { name: 'Send follow-up', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Retry previous request' })).toBeVisible()
    await page.reload()
    await input.fill('Another question for later')
    const retry = page.getByRole('button', { name: 'Retry previous request' })
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Illustrative: compare 9/10 with 6/10.')).toBeVisible()
    await expect(input).toHaveValue('Another question for later')
    await expect(page.getByRole('link', { name: 'latest saved follow-up' })).toHaveAttribute(
      'href',
      '/answers/child',
    )
    await expect(retry).toHaveCount(0)
    expect(generations).toBe(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
