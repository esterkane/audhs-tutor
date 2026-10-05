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
      await expectOk(
        await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
      )
      const explanation = Array.from(
        { length: 12 },
        (_, i) =>
          `### Worked example ${i + 1}\n\nCompare two short lists of numbers. Multiply matching entries, then add those products. Notice that magnitude affects the total as well as direction. This prepared text tests reading and navigation, not model quality.`,
      ).join('\n\n')
      let calls = 0
      let gradingCalls = 0
      page.on('request', (request) => {
        if (request.url().endsWith('/api/assess/attempt') && request.method() === 'POST') gradingCalls++
      })
      await page.route('**/api/tutor/stream', async (route) => {
        calls++
        await route.fulfill({
          contentType: 'text/event-stream',
          body:
            `event: token\ndata: ${JSON.stringify({ text: explanation })}\n\n` +
            `event: done\ndata: ${JSON.stringify({ turn_id: 'reading-fixture', model_call_id: null, tutor_trace_id: 'fixture', registry_id: null, route: null, representation: null, sentences: 12, latency_ms: 1, outcome: 'ok', text: explanation, sources: [], dropped: [], flagged: [] })}\n\n`,
        })
      })
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      const lastSection = page.getByRole('heading', { name: 'Worked example 12', exact: true })
      await page
        .getByRole('combobox', { name: 'Choose a section' })
        .selectOption({ label: '12. Worked example 12' })
      await expect(lastSection).toBeVisible()
      await page
        .getByLabel('Your notes for this section (optional)')
        .fill('Check how magnitude changes the result.')
      const question = page.getByRole('button', { name: /^(Try a question|Return to your question)$/ })
      await question.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      await expect(lastSection).not.toBeVisible()
      // The first two seeded questions are MCQ then cloze, both deterministically graded.
      const choices = page.getByRole('button', { name: '13', exact: true })
      if (await choices.isVisible()) await choices.click()
      else await page.getByLabel('Your answer', { exact: true }).fill('no idea')
      const graded = page.waitForResponse((response) => response.url().endsWith('/api/assess/attempt') && response.request().method() === 'POST')
      await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      const outcome = await (await graded).json()
      expect(outcome.score).toBeLessThan(0.85)
      expect(outcome.confidence_pre).toBeNull()
      await expect(page.getByRole('heading', { name: 'Feedback on your answer' })).toBeVisible()

      await page.screenshot({ path: info.outputPath('question.png'), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const back = page.getByRole('button', { name: 'Revisit the explanation', exact: true })
      await back.focus()
      await page.keyboard.press('Enter')
      await expect(lastSection).toBeVisible()
      expect(calls).toBe(1)
      await question.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Feedback on your answer' })).toBeVisible()
      await expect(page.getByText(outcome.feedback, { exact: true })).toBeVisible()
      expect(gradingCalls).toBe(1)
      await page.getByRole('button', { name: 'Revisit the explanation', exact: true }).click()
      await page.reload()
      await expect(lastSection).toBeVisible()
      expect(calls).toBe(1)
      await expect(question).toBeVisible()
      await expect(page.getByRole('combobox', { name: 'Choose a section' })).toHaveValue('11')
      await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue(
        'Check how magnitude changes the result.',
      )
      await page.screenshot({ path: info.outputPath('reading.png'), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await question.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
      expect(calls).toBe(1)
    } finally {
      await endOpenSession(request)
    }
  })
}
