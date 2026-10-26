import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`unchanged checked reply can be reused at capacity ${width}`, async ({ page, request }) => {
    const source = 'Python 3:\nvalue = 3\n'
    const legacy = Array.from({ length: 11 }, (_, i) => ({ action: 'discuss', request: `Earlier request ${i}`, model_call_id: `legacy-${i}`, answer: { discussion: `Earlier saved reply ${i}` } }))
    const response = await request.post(`${API}/api/knowledge-material/drafts`, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: { title: 'Synthetic capacity research', notes: source, workflow_step: 'research', research: { passage: source, topic: 'Python addition', current: 0, questions: [{ id: 'q', prompt: 'What does `value + 1` return?', findings: 'Check this addition.', tutor_exchanges: legacy }] } },
    })
    await expectOk(response)
    const draft = await response.json()
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/curriculum?draft=${draft.id}`)
    await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
    const endpoint = `/drafts/${draft.id}/research-tutor`
    const firstReply = page.waitForResponse(r => r.url().endsWith(endpoint))
    await page.getByRole('button', { name: 'Discuss my findings locally', exact: true }).click()
    const saved = await (await firstReply).json()
    const history = saved.payload.authoring.research.questions[0].tutor_exchanges
    expect(history).toHaveLength(12)
    expect(history.at(-1).calculation).toBe('python.literal-expression.v1')
    await expect(page.getByRole('button', { name: 'Discuss my findings locally', exact: true })).toBeDisabled()
    const reuse = page.waitForResponse(r => r.url().endsWith(endpoint))
    await page.getByRole('button', { name: 'Reuse saved reply', exact: true }).click()
    const repeated = await (await reuse).json()
    expect(repeated.reused).toBe(true)
    expect(repeated.payload.authoring.research.questions[0].tutor_exchanges).toEqual(history)
    await page.reload()
    await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
    await expect(page.getByRole('button', { name: 'Reuse saved reply', exact: true })).toBeEnabled()
    await expect(page.getByText('Earlier tutor replies (11)', { exact: true })).toBeVisible()
    const fresh = await request.post(`${API}/api/knowledge-material/drafts/${draft.id}/research-tutor`, { data: { expected_version: repeated.version, question_id: 'q', action: 'draft' } })
    expect(fresh.status()).toBe(422)
    expect((await fresh.json()).error.code).toBe('research_history_full')
  })
}
