import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`reported questions remain readable after a failed refresh ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let reportId = ''
    try {
      const start = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(start)
      const session = await start.json()
      const next = await request.get(`${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`)
      await expectOk(next)
      const { item } = await next.json()
      const report = await request.post(`${API}/api/areas/feedback/questions`, { data: {
        assessment_id: item.id, verdict: 'bad', labels: ['too_vague'], note: `Synthetic report at ${width}`,
      } })
      await expectOk(report)
      reportId = (await report.json()).id
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences#question-reports')
      const panel = page.locator('#question-reports')
      await panel.getByRole('button', { name: 'Show question reports' }).focus()
      await page.keyboard.press('Enter')
      await expect(panel.getByText(`Your note: Synthetic report at ${width}`)).toBeVisible()
      await expect(panel.getByText('Content unchanged since this report.')).toBeVisible()
      await page.route('**/api/questions/corrections?*', route => route.fulfill({ status: 503, json: { error: { message: 'Synthetic outage' } } }))
      await panel.getByRole('button', { name: 'Refresh question reports' }).click()
      await expect(panel.getByRole('alert')).toBeVisible()
      await expect(panel.getByText(`Your note: Synthetic report at ${width}`)).toBeVisible()
      await panel.screenshot({ path: `/tmp/correction-inbox-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await page.unroute('**/api/questions/corrections?*')
      await panel.getByRole('button', { name: 'Refresh question reports' }).focus()
      await page.keyboard.press('Enter')
      await expect(panel.getByRole('alert')).toHaveCount(0)
      await panel.getByRole('button', { name: 'Hide question reports' }).click()
      await expect(panel.getByText(`Your note: Synthetic report at ${width}`)).toHaveCount(0)
    } finally {
      if (reportId) await expectOk(await request.delete(`${API}/api/areas/feedback/questions/${reportId}`))
      await endOpenSession(request)
    }
  })
}
