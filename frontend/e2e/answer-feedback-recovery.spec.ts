import { expect, test, type Route } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`feedback loading can time out and retry without losing the saved answer (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 })
    await page.clock.install()
    await page.route('**/api/answers/fixture', (route) => route.fulfill({ json: {
      id: 'fixture', request_text: 'Why compare groups?', text: 'Compare before and after counts.',
      surface: 'playground', created_at: '2026-10-01T10:00:00Z', request: {}, metadata: {}, turn_id: 'fixture',
    } }))
    let initial: Route | undefined
    let gets = 0
    let ready = false
    await page.route('**/api/answers/fixture/feedback', (route) => {
      if (route.request().method() === 'PUT') return route.fulfill({ json: {
        ...route.request().postDataJSON(), revision: 1,
      } })
      gets++
      if (!ready) { initial = route; return }
      return route.fulfill({ json: { verdict: null, note: '', hidden: false, revision: 0 } })
    })
    await page.goto('/answers/fixture')
    await expect(page.getByText('Compare before and after counts.')).toBeVisible()
    await expect(page.getByText('Loading feedback…', { exact: true })).toBeVisible()
    await page.clock.fastForward(16000)
    const retry = page.getByRole('button', { name: 'Retry feedback', exact: true })
    await expect(retry).toBeVisible()
    await expect(page.getByText('Compare before and after counts.')).toBeVisible()
    ready = true
    await retry.focus()
    await page.keyboard.press('Enter')
    const note = page.getByRole('textbox', { name: 'Why? (optional)', exact: true })
    await note.fill('Explain the denominator.')
    await initial?.fulfill({ json: { verdict: 'incorrect', note: 'Old response', hidden: true, revision: 99 } }).catch(() => {})
    await expect(note).toHaveValue('Explain the denominator.')
    await page.getByRole('button', { name: 'Save feedback', exact: true }).click()
    await expect(page.getByText('Feedback saved.', { exact: true })).toBeVisible()
    expect(gets).toBeGreaterThanOrEqual(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
