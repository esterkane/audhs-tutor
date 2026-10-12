import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk } from './helpers'

for (const width of [320, 1280]) {
  test(`open saved lesson explanations without inference ${width}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      for (const key of ['goal.area', 'goal.course']) {
        await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value: '' } }))
      }
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      const draft = page.getByLabel('Ask about this lesson (optional)')
      await draft.fill('Keep my question while I read history.')
      const before = await currentSession(request)
      const writes: string[] = []
      page.on('request', req => {
        if (req.url().includes('/api/') && req.method() !== 'GET') writes.push(req.url())
      })
      const saved = page.getByRole('link', { name: 'Read saved explanations', exact: true })
      await expect(saved).toHaveAttribute('href', `/answers?skill_id=${before?.state?.skill_id}&surface=tutor`)
      expect((await saved.boundingBox())!.height).toBeGreaterThanOrEqual(44)
      await saved.focus()
      await page.screenshot({ path: info.outputPath('saved-entry.png'), fullPage: true })
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(/\/answers\?skill_id=.+&surface=tutor$/)
      await expect(page.getByText('Filtered to the selected learning context.')).toBeVisible()
      await expect(page.getByRole('combobox', { name: /^Show/ })).toHaveValue('tutor')
      await page.goBack()
      await expect(draft).toHaveValue('Keep my question while I read history.')
      expect(await currentSession(request)).toEqual(before)
      expect(writes).toEqual([])
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    } finally {
      await endOpenSession(request)
    }
  })
}
