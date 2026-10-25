import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) test(`evidence-first assessment feedback ${width}`, async ({ page, request }, info) => {
  await endOpenSession(request)
  try {
    await page.setViewportSize({ width, height: 900 })
    await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
    await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
    await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: freshDeterministicSkill() } }))
    let submissions = 0
    await page.route('**/api/assess/attempt', route => {
      submissions++
      return route.fulfill({ json: {
        revision_of_attempt_id: width === 390 ? 'original-attempt' : null, review_updated: width !== 390,
        answer_id: 'saved-assessment', assessment_id: route.request().postDataJSON().assessment_id, attempt_id: 'fixture-attempt', score: 0.5, mastery: 0.4,
        feedback: 'The denominator changes the proportion.', next_step: 'Compare the proportions next.',
        grader_level: 'deterministic', confidence_pre: null, review: { due: '2026-10-12T12:00:00Z' },
        criterion_results: [
          { criterion: 'Compare proportions', passed: false, evidence: 'Only totals were compared.' },
          { criterion: 'Identify groups', passed: true, evidence: 'Both groups were named.' },
        ],
      } })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /^Continue$/ }).click()
    const choices = page.getByRole('group', { name: 'Your answer', exact: true })
    await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
    if (await choices.count()) await choices.getByRole('button').first().click()
    else await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill('5')
    await page.getByRole('button', { name: 'Check my answer', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'What was right', exact: true })).toBeVisible()
    const headings = await page.locator('h4').allTextContents()
    expect(headings.indexOf('What was right')).toBeLessThan(headings.indexOf('Not quite — what to reconsider'))
    expect(headings.indexOf('Not quite — what to reconsider')).toBeLessThan(headings.indexOf('Why'))
    await expect(page.getByText('Mastery estimate after this attempt 40%')).not.toBeVisible()
    const details = page.locator('summary').filter({ hasText: /^Score and grading details$/ })
    await details.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Mastery estimate after this attempt 40%')).toBeVisible()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled()
    if (width === 390) {
      await expect(page.getByText(/Repeated practice on a previously checked question/)).toBeVisible()
      await expect(page.getByText(/Existing review schedule unchanged/)).toBeVisible()
      await expect(page.getByText(/Review scheduled after this attempt/)).toHaveCount(0)
    }
    const helpRequests: { action: string; text: string; assessment_answer_id: string }[] = []
    await page.route('**/api/tutor/stream', route => {
      helpRequests.push(route.request().postDataJSON())
      const text = `Help response ${helpRequests.length}`
      return route.fulfill({ contentType: 'text/event-stream', body:
        `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ turn_id: `help-${helpRequests.length}`, outcome: 'ok', text, sources: [], dropped: [], flagged: [] })}\n\n`,
      })
    })
    for (const [index, label] of ['Show a hint', 'Explain the difficult part', 'Show another example', 'See full solution'].entries()) {
      const control = page.getByRole('button', { name: label, exact: true })
      await control.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText(`Help response ${index + 1}`, { exact: true })).toBeVisible()
      await expect(control).toBeEnabled()
      await expect(page.getByRole('heading', { name: 'What was right', exact: true })).toBeVisible()
    }
    expect(helpRequests.map(r => r.action)).toEqual(['hint', 'explain', 'explain', 'full_solution'])
    expect(helpRequests.every(r => r.assessment_answer_id === 'saved-assessment')).toBe(true)
    expect(submissions).toBe(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await page.getByRole('heading', { name: 'Feedback on your answer' }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('feedback.png') })
    await page.getByRole('button', { name: 'See full solution', exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('feedback-help.png') })
  } finally { await endOpenSession(request) }
})
