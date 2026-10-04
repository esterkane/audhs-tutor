import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`interrupted assessment recovery ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
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
      // Exercise the staged-result UI using a simulated lookup. The real finish
      // endpoint replays the already committed result; backend tests separately
      // inject interruption before evidence writes and verify staged application.
      await page.route('**/api/assess/requests/**', async (route) => {
        if (route.request().method() === 'GET')
          await route.fulfill({ json: { status: 'grade_ready', result: null } })
        else await route.continue()
      })
      await lookup.focus()
      await page.keyboard.press('Enter')
      const finish = page.getByRole('button', { name: 'Finish saving this result', exact: true })
      await expect(finish).toBeVisible()
      await finish.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Feedback on the original submission' })).toBeVisible()
      await expect(page.getByRole('link', { name: 'Open saved feedback', exact: true })).toBeVisible()
      expect(submissions).toBe(1)
    } finally {
      await endOpenSession(request)
    }
  })
}
