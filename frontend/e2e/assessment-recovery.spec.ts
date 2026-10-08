import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const recoveryState of ['grade_ready', 'prepared_ready', 'unresolved'] as const) {
for (const narrow of [false, true]) {
  test(`interrupted assessment ${recoveryState} recovery ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
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
        await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: freshDeterministicSkill() } }),
      )
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      const choices = page.getByRole('group', { name: 'Your answer', exact: true })
      if (await choices.count()) await choices.getByRole('button').first().click()
      else await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill('5')
      let submissions = 0
      await page.route('**/api/assess/attempt', async (route) => {
        submissions++
        const committed = await route.fetch()
        await expectOk(committed)
        await route.abort('failed')
      })
      await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      await expect(page.getByRole('region', { name: 'Submission recovery' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Check saved result', exact: true })).toBeEnabled()
      await page.reload()
      const lookup = page.getByRole('button', { name: 'Check saved result', exact: true })
      await expect(lookup).toBeVisible()
      // Exercise both recovery presentations using a simulated lookup. The real
      // endpoint replays an already committed result; backend tests separately
      // prove hard-exit eligibility and exact-once application on continuation.
      await page.route('**/api/assess/requests/**', async (route) => {
        if (route.request().method() === 'GET')
          await route.fulfill({ json: { status: recoveryState, result: null, local_worker_stopped: recoveryState === 'unresolved' } })
        else await route.continue()
      })
      await lookup.focus()
      await page.keyboard.press('Enter')
      if (recoveryState === 'unresolved') {
        const panel = page.getByRole('region', { name: 'Submission recovery' })
        await expect(panel.getByText(/The local grading worker has stopped/)).toBeVisible()
        await expect(panel.getByRole('button', { name: /Continue saved submission|Send the original answer/ })).toHaveCount(0)
        await expect(lookup).toBeFocused()
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
        await panel.screenshot({ path: `/tmp/assessment-stopped-${narrow ? 'narrow' : 'desktop'}.png` })
        expect(submissions).toBe(1)
        return
      }
      const finish = page.getByRole('button', { name: recoveryState === 'prepared_ready' ? 'Continue saved submission' : 'Finish saving this result', exact: true })
      await expect(finish).toBeVisible()
      await page.keyboard.press('Tab')
      await expect(finish).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
      if (recoveryState === 'prepared_ready') {
        await page.getByRole('region', { name: 'Submission recovery' }).screenshot({ path: `/tmp/assessment-continue-${narrow ? 'narrow' : 'desktop'}.png` })
      }
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Feedback on the original submission' })).toBeVisible()
      await expect(page.getByRole('link', { name: 'Open saved feedback', exact: true })).toBeVisible()
      expect(submissions).toBe(1)
    } finally {
      await endOpenSession(request)
    }
  })
}

}
