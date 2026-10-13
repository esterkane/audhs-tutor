import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) test(`delayed end response respects navigation ${width}`, async ({ page, request }, info) => {
  await endOpenSession(request)
  let release!: () => void
  const delivery = new Promise<void>(resolve => { release = resolve })
  try {
    await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await page.locator('summary').filter({ hasText: /^Session options$/ }).click()
    let committed!: () => void
    const ready = new Promise<void>(resolve => { committed = resolve })
    let delivered!: () => void
    const done = new Promise<void>(resolve => { delivered = resolve })
    await page.route('**/api/sessions/*/end', async route => {
      const response = await route.fetch()
      await expectOk(response)
      committed()
      await delivery
      await route.fulfill({ response })
      delivered()
    })
    await page.getByRole('button', { name: 'End session', exact: true }).click()
    await ready
    await page.getByRole('link', { name: 'Preferences', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/preferences$/)
    release()
    await done
    await page.waitForTimeout(200)
    await expect(page).toHaveURL(/\/preferences$/)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: info.outputPath('preferences-after-end.png'), fullPage: true })
  } finally { release(); await endOpenSession(request) }
})
