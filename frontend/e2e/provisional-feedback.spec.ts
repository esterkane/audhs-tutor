import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`provisional feedback remains advisory after reload ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    let assessmentId = ''
    const skill = freshDeterministicSkill()
    let feedbackId = 'feedback-one'
    const result = () => ({ outcome: 'provisional_feedback', policy_version: 'model-feedback.v1', feedback_id: feedbackId, answer_id: 'advisory-answer', assessment_id: assessmentId, session_id: session.id, skill_id: skill, content_version: 'fixture-one', feedback: 'Compare the training and held-out sets.', next_step: 'Explain which set fits the parameter.', model_route: 'local', criterion_feedback: [{ criterion: 'Fit using training data', observation: 'Model suggests expanding your explanation.' }] })
    try {
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: skill } }))
      await page.route('**/api/assess/next?*', async route => {
        const response = await route.fetch()
        const data = await response.json()
        assessmentId = data.item.id
        data.item = { ...data.item, kind: 'explain_back', question: 'Which data should fit the parameter?', options: null, criteria: ['Fit using training data'], content_version: 'fixture-one' }
        await route.fulfill({ response, json: data })
      })
      await page.route('**/api/assess/attempt', route => {
        if (route.request().postDataJSON().revision_of_feedback_id) {
          expect(route.request().postDataJSON().revision_of_feedback_id).toBe('feedback-one')
          expect(route.request().postDataJSON().revision_of_attempt_id).toBeUndefined()
          feedbackId = 'feedback-two'
        }
        return route.fulfill({ json: result() })
      })
      await page.route('**/api/assess/feedback/feedback-one/revision?*', route => route.fulfill({ json: {
        feedback_id: 'feedback-one', root_feedback_id: 'feedback-one', answer: 'Use the training data.',
        item: { id: assessmentId, skill_id: skill, kind: 'explain_back', question: 'Which data should fit the parameter?', content_version: 'fixture-one' },
      } }))
      await page.route('**/api/assess/requests/*?*', route => route.fulfill({ json: { status: 'completed', result: result() } }))
      await page.route('**/api/answers/advisory-answer/feedback', route => route.fulfill({ json: { verdict: null, note: '', hidden: false, revision: 0 } }))
      await page.route('**/api/answers/advisory-answer', route => route.fulfill({ json: {
        id: 'advisory-answer', surface: 'assessment', request: { text: 'Which data should fit the parameter?', learner_answer_display: 'Use the training data.' },
      } }))
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.locator('#answer').fill('Use the training data.')
      await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      await expect(page.getByRole('heading', { name: 'Model feedback — not an assessed result' })).toBeVisible()
      await page.reload()
      await expect(page.getByRole('heading', { name: 'Model feedback — not an assessed result' })).toBeVisible()
      await expect(page.getByText('Score and grading details')).toHaveCount(0)
      await expect(page.getByText(/Scores and review dates describe/)).toHaveCount(0)
      const observations = page.locator('summary').filter({ hasText: 'Model observations against the rubric' })
      await observations.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText(/Model suggests expanding/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Listen to feedback' })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      const discussion = page.locator('summary').filter({ hasText: 'Discuss this feedback' })
      await discussion.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Your recorded answer', exact: true })).toBeVisible()
      await expect(page.getByText('Use the training data.', { exact: true })).toBeVisible()
      await page.getByLabel('Your follow-up question', { exact: true }).fill('Why only training data?')
      await expect(page.getByRole('button', { name: 'Send follow-up', exact: true })).toBeEnabled()
      await page.getByRole('button', { name: 'Try again', exact: true }).click()
      await expect(page.locator('#answer')).toHaveValue('Use the training data.')
      await page.locator('#answer').fill('Fit the median on training data and reuse it.')
      await page.reload()
      await expect(page.locator('#answer')).toHaveValue('Fit the median on training data and reuse it.')
      await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      await expect(page.getByRole('heading', { name: 'Model feedback — not an assessed result' })).toBeVisible()
      expect(feedbackId).toBe('feedback-two')
      await page.screenshot({ path: `/tmp/provisional-feedback-${width}.png`, fullPage: true })
    } finally { await endOpenSession(request) }
  })
}
