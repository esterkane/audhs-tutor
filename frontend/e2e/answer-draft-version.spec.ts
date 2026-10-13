import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`changed question does not reuse an old choice at ${width}px`, async ({ page, request }) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    try {
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: freshDeterministicSkill() } }))
      let changed = false
      await page.route('**/api/assess/next?*', async route => {
        const response = await route.fetch()
        const data = await response.json()
        data.item = { ...data.item, kind: 'mcq', question: changed ? 'New question: choose the even number.' : 'Old question: choose the odd number.', options: changed ? ['3', '4'] : ['3', '2'], content_version: changed ? 'version-two' : 'version-one' }
        await route.fulfill({ response, json: data })
      })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      const choices = page.getByRole('group', { name: 'Your answer', exact: true })
      await choices.getByRole('button', { name: '3', exact: true }).click()
      changed = true
      await page.reload()
      await expect(page.getByText('New question: choose the even number.')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeDisabled()
      const history = page.locator('summary').filter({ hasText: 'Earlier answer drafts' })
      await history.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Old question: choose the odd number.')).toBeVisible()
      await choices.getByRole('button', { name: '4', exact: true }).click()
      await page.reload()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeEnabled()
      await page.locator('summary').filter({ hasText: 'Earlier answer drafts' }).click()
      await expect(page.getByText('Old question: choose the odd number.')).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.screenshot({ path: `/tmp/answer-version-${width}.png`, fullPage: true })
    } finally { await endOpenSession(request) }
  })
}
