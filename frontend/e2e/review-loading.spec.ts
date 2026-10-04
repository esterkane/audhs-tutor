import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`review failure remains recoverable at ${width}px`, async ({ page, request }) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
    let fail = true
    await page.route('**/api/review/due?*', async (route) => {
      if (fail) await route.fulfill({ status: 503, json: { error: { code: 'offline', message: 'Offline' } } })
      else await route.fulfill({ json: { items: [], cap: 5, total_due: 0, as_of: 'now' } })
    })
    try {
      await page.goto('/')
      await page.getByRole('button', { name: /^Resume previous session/ }).click()
      await page.goto('/review')
      await expect(page.getByRole('alert')).toContainText('Could not load review cards')
      await expect(page.getByRole('heading', { name: 'Review done' })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Stop session', exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Go to Home', exact: true })).toBeVisible()
      fail = false
      await page.getByRole('button', { name: 'Retry', exact: true }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Review done' })).toBeVisible()
      await expect(page.getByText('Nothing is due right now.')).toBeVisible()
    } finally {
      await endOpenSession(request)
    }
  })
}
