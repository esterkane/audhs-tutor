import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`failed session load offers keyboard retry and Home at ${width}px`, async ({ page, request }) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    let fail = true
    await page.route(`**/api/sessions/${session.id}`, async (route) => {
      if (fail)
        await route.fulfill({
          status: 503,
          json: { error: { code: 'unavailable', message: 'Service unavailable' } },
        })
      else await route.continue()
    })
    try {
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await expect(page.getByRole('alert')).toContainText('Could not load this session')
      await expect(page.getByRole('button', { name: 'Go to Home', exact: true })).toBeVisible()
      fail = false
      const retry = page.getByRole('button', { name: 'Retry loading session' })
      await retry.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Choose where to begin' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'End session', exact: true })).toBeVisible()
    } finally {
      await endOpenSession(request)
    }
  })
}
