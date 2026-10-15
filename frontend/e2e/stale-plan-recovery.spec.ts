import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [1280, 390]) {
 for (const action of ['proposal', 'undo']) {
  test(`${action} review preserves the current activity at ${width}px`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      const started = await request.post(`${API}/api/sessions`, { data: { energy: 5 } })
      await expectOk(started)
      const { id } = await started.json()
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: id, index: 0 } }))
      const replanned = await request.post(`${API}/api/plan/replan`, { data: { session_id: id, energy: 1 } })
      await expectOk(replanned)
      const aid = (await replanned.json()).proposal_id
      expect(aid).toBeTruthy()
      if (action === 'undo') await expectOk(await request.post(`${API}/api/adaptations/${aid}/decide`, { data: { decision: 'try', session_id: id } }))
      await expectOk(await request.post(`${API}/api/plan/blocks/next`, { data: { session_id: id, from_index: 0 } }))
      const before = await (await request.get(`${API}/api/sessions/${id}`)).json()
      await page.setViewportSize({ width, height: 900 })
      await page.goto(action === 'undo' ? '/preferences' : '/')
      if (action === 'proposal') await page.getByText(/Optional learning adjustments/).click()
      const review = page.getByRole('button', { name: 'Review an updated plan', exact: true }).first()
      await review.focus()
      await page.keyboard.press('Enter')
      const heading = page.getByRole('heading', { name: 'Updated plan — not applied' })
      await expect(heading).toBeFocused()
      const afterPreview = await (await request.get(`${API}/api/sessions/${id}`)).json()
      expect(afterPreview.plan).toEqual(before.plan)
      expect(afterPreview.checkpoint).toEqual(before.checkpoint)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('updated-plan-preview.png'), fullPage: true })
      const apply = page.getByRole('button', { name: 'Apply reviewed plan', exact: true })
      await apply.focus()
      await page.keyboard.press('Enter')
      await expect(heading).not.toBeVisible()
      const after = await (await request.get(`${API}/api/sessions/${id}`)).json()
      expect(after.plan.slice(0, 2)).toEqual(before.plan.slice(0, 2))
      expect(after.state.block_started_at).toBe(before.state.block_started_at)
    } finally {
      await endOpenSession(request)
    }
  })
}
}
