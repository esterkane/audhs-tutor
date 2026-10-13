import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`answer storage failure is visible at ${width}px`, async ({ page, request }) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() => {
      const original = Storage.prototype.setItem
      Storage.prototype.setItem = function(key, value) {
        if (key.startsWith('audhs-question-drafts:')) throw new DOMException('Quota', 'QuotaExceededError')
        original.call(this, key, value)
      }
    })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    try {
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: freshDeterministicSkill() } }))
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      const choices = page.getByRole('group', { name: 'Your answer', exact: true })
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      if (await choices.count()) {
        await choices.getByRole('button').first().focus()
        await page.keyboard.press('Enter')
      } else {
        await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill('My unfinished reasoning')
      }
      await expect(page.getByRole('alert').filter({ hasText: 'could not save your answer' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeEnabled()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.screenshot({ path: `/tmp/answer-storage-${width}.png`, fullPage: true })
    } finally { await endOpenSession(request) }
  })
}
