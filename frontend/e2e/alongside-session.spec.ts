import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`work alongside retains the lesson and draft ${width}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      await page.setViewportSize({ width, height: 900 })
      const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(started)
      const session = await started.json()
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      const input = page.getByLabel('Ask about this lesson (optional)')
      await input.fill('Keep this question while I work.')
      const writes: string[] = []
      page.on('request', request => {
        if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url())
      })
      const toggle = page.locator('main summary').filter({ hasText: /^Work alongside$/ })
      await toggle.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Working alongside' })).toBeVisible()
      await expect(input).toBeVisible()
      await expect(input).toHaveValue('Keep this question while I work.')
      await expect(page.getByRole('link', { name: 'Back to the session' })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Stop brown noise' })).toHaveCount(0)
      await page.screenshot({ path: info.outputPath('alongside-open.png'), fullPage: true })
      await toggle.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Working alongside' })).toHaveCount(0)
      await expect(input).toHaveValue('Keep this question while I work.')
      expect(writes).toEqual([])
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    } finally { await endOpenSession(request) }
  })
}
