import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`saved assessment feedback ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }, info) => {
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
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      const choices = page.getByRole('group', { name: 'Your answer', exact: true })
      if (await choices.count())
        await (narrow ? choices.getByRole('button').last() : choices.getByRole('button').first()).click()
      else await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill(narrow ? '0' : '5')
      const gradeResponse = page.waitForResponse(
        (response) =>
          response.url().endsWith('/api/assess/attempt') && response.request().method() === 'POST',
      )
      await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      const grade = await (await gradeResponse).json()
      expect(grade.correct).toBe(!narrow)
      const saved = page.getByRole('link', { name: 'Open saved feedback', exact: true })
      await expect(saved).toBeVisible()
      await expect(page.getByRole('button', { name: 'Explain the idea first', exact: true })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Give me a hint', exact: true })).toHaveCount(0)
      let extraAttempts = 0
      page.on('request', (request) => {
        if (request.method() === 'POST' && request.url().endsWith('/api/assess/attempt')) extraAttempts++
      })
      let helpCalls = 0
      await page.route('**/api/tutor/stream', async (route) => {
        helpCalls++
        expect(route.request().postDataJSON()).toMatchObject({ session_id: session.id, action: 'explain' })
        const done = {
          turn_id: 'feedback-concept',
          text: 'Compare matching components in a similar example.',
          sources: [],
          dropped: [],
        }
        await route.fulfill({
          contentType: 'text/event-stream',
          body: `event: token\ndata: ${JSON.stringify({ text: done.text })}\n\nevent: done\ndata: ${JSON.stringify(done)}\n\n`,
        })
      })
      const help = page.getByRole('button', {
        name: "I don't understand yet — explain the idea",
        exact: true,
      })
      await expect(help).toBeVisible()
      expect(helpCalls).toBe(0)
      await help.focus()
      await page.keyboard.press('Enter')
      await expect(
        page.getByText('Compare matching components in a similar example.', { exact: true }),
      ).toBeVisible()
      await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toBeVisible()
      expect(extraAttempts).toBe(0)
      expect(helpCalls).toBe(1)
      await page.screenshot({ path: info.outputPath('feedback-help.png'), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const writes: string[] = []
      page.on('request', (request) => {
        if (request.method() === 'POST') writes.push(request.url())
      })
      await saved.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Feedback on your past attempt' })).toBeVisible()
      const details = page.getByText('Question and grading details at the time', { exact: true })
      await details.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Grading method: deterministic')).toBeVisible()
      await page.reload()
      await expect(page.getByRole('heading', { name: 'Feedback on your past attempt' })).toBeVisible()
      expect(writes).toEqual([])
      await page.goto('/answers?surface=assessment')
      await expect(page.getByRole('combobox', { name: 'Show', exact: true })).toHaveValue('assessment')
    } finally {
      await endOpenSession(request)
    }
  })
}
