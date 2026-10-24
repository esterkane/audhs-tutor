import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const [language, width] of [['en', 1280], ['de', 390]] as const) {
  test(`checked research stays editable after reload in ${language} at ${width}`, async ({ page, request }) => {
    const preferences = (await (await request.get(`${API}/api/preferences`)).json()).values
    try {
      for (const [key, value] of [['tutor.persona', 'kangaroo'], ['tutor.response_language', language]])
        await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value } }))
      const source = "In Python, text = 'go'. text * -3 returns ''. text * 0 returns ''. text * 2 returns 'gogo'."
      const response = await request.post(`${API}/api/knowledge-material/drafts`, {
        headers: { 'Idempotency-Key': crypto.randomUUID() },
        data: { title: `Synthetic checked research ${language}`, notes: source, workflow_step: 'research', research: {
          passage: source, topic: 'Python repetition', current: 0,
          questions: [{ id: 'q', prompt: language === 'de'
            ? 'Was geben text * -3, text * 0 und text * 2 zurück, und ändert sich text?'
            : 'What do text * -3, text * 0 and text * 2 return, and does text change?', findings: 'Check the original value and all results.' }],
        } },
      })
      await expectOk(response)
      const draft = await response.json()
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`/curriculum?draft=${draft.id}`)
      await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
      const reply = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}/research-tutor`))
      await page.getByRole('button', { name: 'Draft one section locally', exact: true }).click()
      const saved = await (await reply).json()
      const exchange = saved.payload.authoring.research.questions[0].tutor_exchanges[0]
      expect(exchange.calculation).toBe('python.string-repetition.v1')
      expect(exchange.model_call_id).toBeNull()
      expect(exchange.answer.source_quotes).toEqual([source])
      expect(exchange.answer.section).toContain(language === 'de' ? 'unverändert' : 'unchanged')
      await expect(page.getByText(/Checked Python calculation; no model was used/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Ask for another reply', exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: 'Use tutor draft in my section', exact: true }).click()
      await page.getByRole('button', { name: '3. Write', exact: true }).click()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(exchange.answer.section)
      await page.getByRole('button', { name: 'Add section to explanation', exact: true }).click()
      const write = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}`) && r.request().method() === 'PUT')
      await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
      await expectOk(await write)
      await page.reload()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toBeEnabled()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(exchange.answer.section)
      await page.getByRole('button', { name: '4. Review', exact: true }).click()
      await page.locator('summary').filter({ hasText: 'Shape a lesson (optional)' }).click()
      await expect(page.getByRole('textbox', { name: 'Learning objective', exact: true })).toBeEnabled()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    } finally {
      for (const key of ['tutor.persona', 'tutor.response_language'])
        await request.put(`${API}/api/preferences`, { data: { key, value: preferences[key] } })
    }
  })
}
