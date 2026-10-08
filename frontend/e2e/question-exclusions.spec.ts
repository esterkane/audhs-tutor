import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`exclude and restore a question with real sandbox state ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let assessmentId = ''
    try {
      for (const key of ['goal.area', 'goal.course']) await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.route('**/api/tutor/stream', route => route.fulfill({ contentType: 'text/event-stream', body:
        'event: token\ndata: {"text":"Multiply corresponding entries, then add the products. This is synthetic teaching text."}\n\n' +
        `event: done\ndata: ${JSON.stringify({ turn_id: 'exclusion-fixture', model_call_id: null, tutor_trace_id: 'fixture', registry_id: null, route: null, representation: null, sentences: 2, latency_ms: 1, outcome: 'ok', text: 'Multiply corresponding entries, then add the products.', sources: [], dropped: [], flagged: [] })}\n\n` }))
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      await page.getByRole('button', { name: /^(Try a question|Return to your question)$/ }).click()
      const options = page.getByRole('button', { name: 'Question practice options' })
      await options.focus()
      await page.keyboard.press('Enter')
      await page.getByLabel('Reason (optional)').fill('Synthetic test: wrong context')
      const saved = page.waitForResponse(r => r.url().includes('/api/questions/') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      const result = await (await saved).json()
      assessmentId = result.assessment_id
      expect(result.state).toBe('suspended')
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeDisabled()
      await expect(page.getByText('Question choice changed. Your answer draft is kept. Choose another question to continue.')).toBeVisible()
      await page.getByRole('link', { name: 'Manage excluded questions' }).click()
      await page.getByRole('button', { name: 'Show excluded questions' }).click()
      await expect(page.getByText('Reason: Synthetic test: wrong context')).toBeVisible()
      await page.reload()
      await page.getByRole('button', { name: 'Show excluded questions' }).click()
      await page.getByRole('button', { name: 'Question practice options' }).click()
      const restore = page.getByRole('button', { name: 'Restore this question', exact: true })
      await restore.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Restored. This question may appear in practice again.')).toBeVisible()
      await expect(page.getByRole('heading', { name: 'Manage question exclusions' })).toBeFocused()
      await page.locator('#excluded-questions').screenshot({ path: `/tmp/question-exclusions-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await page.getByRole('button', { name: 'Refresh exclusions' }).click()
      await expect(page.getByText('0 excluded question(s).')).toBeVisible()
    } finally {
      if (assessmentId) {
        const view = await (await request.get(`${API}/api/questions/${assessmentId}/practice`)).json()
        if (view.status.state === 'suspended') await request.post(`${API}/api/questions/${assessmentId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } })
      }
      await endOpenSession(request)
    }
  })
}
