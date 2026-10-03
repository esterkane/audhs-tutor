import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`stale question explicit refresh ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(
        await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
      )
      await expectOk(
        await request.post(`${API}/api/sessions/${session.id}/checkpoint`, {
          data: { phase: 'assess', skill_id: freshDeterministicSkill() },
        }),
      )
      // Simulate a displayed token invalidated by a server restart. Real API rejects it.
      await page.route('**/api/assess/next?*', async (route) => {
        const response = await route.fetch()
        const data = await response.json()
        data.item.content_version = 'ac1.expired-display'
        await route.fulfill({ response, json: data })
      })
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Resume previous session/ }).click()
      const submit = page.getByRole('button', { name: 'Check my answer', exact: true })
      await expect(submit).toBeVisible()
      const choices = page.getByRole('group', { name: 'Your answer', exact: true })
      const multipleChoice = !!(await choices.count())
      if (multipleChoice) await choices.getByRole('button').first().click()
      else await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill('5')
      const rejected = page.waitForResponse(
        (res) => res.url().includes('/api/assess/attempt') && res.status() === 409,
      )
      await submit.click()
      await rejected
      const recovery = page.getByRole('region', { name: 'Submission recovery' })
      await expect(recovery.getByText(/This submission was not graded/)).toBeVisible()
      await expect(recovery.getByText('Original question and submitted answer')).toBeVisible()
      const refresh = page.getByRole('button', { name: 'Review updated question — keep my answer' })
      await refresh.focus()
      await page.keyboard.press('Enter')
      await expect(refresh).toHaveCount(0)
      await expect(recovery.getByText('Previous question and answer — kept after refresh')).toBeVisible()
      if (multipleChoice) await choices.getByRole('button').first().click()
      else await expect(page.getByRole('textbox', { name: 'Your answer', exact: true })).toHaveValue('5')
      const accepted = page.waitForResponse(
        (res) => res.url().includes('/api/assess/attempt') && res.status() === 200,
      )
      await submit.click()
      await accepted
    } finally {
      await endOpenSession(request)
    }
  })
}
