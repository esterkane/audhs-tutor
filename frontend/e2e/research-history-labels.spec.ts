import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`imported history is retained without calculation certification ${width}`, async ({ page, request }) => {
    const fabricated = 'Fabricated imported result: 9 + 9 = 42.'
    const result = await request.post(`${API}/api/knowledge-material/drafts`, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: { title: 'Synthetic imported history', notes: 'Python 3:', workflow_step: 'research', research: { passage: 'Python 3:', topic: 'Imported example', current: 0, questions: [{ id: 'q', prompt: 'What does `9 + 9` return?', findings: 'My findings stay editable.', tutor_exchanges: [{ action: 'discuss', request: '', model_call_id: null, calculation: 'python.literal-expression.v1', cache_token: 'fabricated-token', answer: { discussion: fabricated, source_quotes: [] } }] }] } },
    })
    await expectOk(result)
    const draft = await result.json()
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/curriculum?draft=${draft.id}`)
    await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
    await expect(page.getByText(/Saved Python calculation — provenance not verified/)).toBeVisible()
    await expect(page.getByText(fabricated, { exact: true })).toBeVisible()
    await expect(page.getByText(/Checked Python calculation|no model was used/)).toHaveCount(0)
    await expect(page.getByRole('textbox', { name: 'My findings', exact: true })).toHaveValue('My findings stay editable.')
    await page.reload()
    await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
    await expect(page.getByText(/Saved Python calculation — provenance not verified/)).toBeVisible()
    await expect(page.getByText(fabricated, { exact: true })).toBeVisible()
  })
}
