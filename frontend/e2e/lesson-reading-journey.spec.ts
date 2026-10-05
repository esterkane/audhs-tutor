import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`long explanation to question and back ${width}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      for (const key of ['goal.area', 'goal.course'])
        await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      const explanation = Array.from({ length: 12 }, (_, i) =>
        `### Worked example ${i + 1}\n\nCompare two short lists of numbers. Multiply matching entries, then add those products. Notice that magnitude affects the total as well as direction. This prepared text tests reading and navigation, not model quality.`,
      ).join('\n\n')
      let calls = 0
      await page.route('**/api/tutor/stream', async (route) => {
        calls++
        await route.fulfill({ contentType: 'text/event-stream', body:
          `event: token\ndata: ${JSON.stringify({ text: explanation })}\n\n` +
          `event: done\ndata: ${JSON.stringify({ turn_id: 'reading-fixture', outcome: 'ok', text: explanation, sources: [], dropped: [], flagged: [] })}\n\n`,
        })
      })
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      const lastSection = page.getByRole('heading', { name: 'Worked example 12', exact: true })
      await page.getByRole('combobox', { name: 'Choose a section' }).selectOption({ label: '12. Worked example 12' })
      await expect(lastSection).toBeVisible()
      await page.getByLabel('Your notes for this section (optional)').fill('Check how magnitude changes the result.')
      const question = page.getByRole('button', { name: 'Try a question', exact: true })
      await question.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      await expect(lastSection).not.toBeVisible()
      await page.screenshot({ path: info.outputPath('question.png'), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const back = page.getByRole('button', { name: 'Back to explanation', exact: true })
      await back.focus()
      await page.keyboard.press('Enter')
      await expect(lastSection).toBeVisible()
      expect(calls).toBe(1)
      await page.reload()
      await expect(lastSection).toBeVisible()
      expect(calls).toBe(1)
      // Current recovery limitation: text survives, but completed-turn reader/actions do not.
      // Keep this baseline explicit until completion metadata is safely restored.
      await expect(question).toHaveCount(0)
      await expect(page.getByRole('combobox', { name: 'Choose a section' })).toHaveCount(0)
      await page.locator('summary').filter({ hasText: /^Saved lesson notes/ }).click()
      await page.locator('summary').filter({ hasText: /^Explanation 1:/ }).click()
      await expect(page.getByText('Check how magnitude changes the result.', { exact: true })).toBeVisible()
      await page.screenshot({ path: info.outputPath('reading.png'), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    } finally {
      await endOpenSession(request)
    }
  })
}
