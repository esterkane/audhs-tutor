import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const [language, width] of [['en', 1280], ['de', 390]] as const) {
  test(`reference research stays editable after reload in ${language} at ${width}`, async ({ page, request }, testInfo) => {
    const preferences = (await (await request.get(`${API}/api/preferences`)).json()).values
    try {
      for (const [key, value] of [['tutor.persona', 'kangaroo'], ['tutor.response_language', language]])
        await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value } }))
      const source = "In Python, strings are immutable. text = 'go'; result = text * 1."
      const response = await request.post(`${API}/api/knowledge-material/drafts`, {
        headers: { 'Idempotency-Key': crypto.randomUUID() },
        data: { title: `Synthetic reference research ${language}`, notes: source, workflow_step: 'research', research: {
          passage: source, topic: 'Python repetition', current: 0,
          questions: [{ id: 'q', prompt: 'Does immutability guarantee a new object? Distinguish == and is.', findings: 'Check the original value and all results.' }],
        } },
      })
      await expectOk(response)
      const draft = await response.json()
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`/curriculum?draft=${draft.id}`)
      const originalQuestion = await page.getByRole('textbox', { name: 'Research question', exact: true }).inputValue()
      await page.getByRole('textbox', { name: 'Research question', exact: true }).fill('')
      await expect(page.getByRole('button', { name: 'Save knowledge material', exact: true })).toBeDisabled()
      await page.reload()
      await expect(page.getByRole('textbox', { name: 'Research question', exact: true })).toHaveValue('')
      await expect(page.getByRole('textbox', { name: 'My findings', exact: true })).toHaveValue('Check the original value and all results.')
      await page.getByRole('textbox', { name: 'Research question', exact: true }).fill(originalQuestion)
      await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
      const reply = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}/research-tutor`))
      await page.getByRole('button', { name: 'Draft one section locally', exact: true }).click()
      const saved = await (await reply).json()
      const exchange = saved.payload.authoring.research.questions[0].tutor_exchanges[0]
      expect(exchange.reference).toBe('python.string-identity.v1')
      expect(exchange.model_call_id).toBeNull()
      expect(exchange.answer.source_quotes).toEqual([source, expect.stringContaining('https://docs.python.org/3.12/reference/datamodel.html')])
      expect(exchange.answer.section).toMatch(language === 'de' ? /^Nein\./ : /^No\./)
      await expect(page.getByText(/Saved reference-based reply — provenance not verified/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Ask for another reply', exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: 'Use tutor draft in my section', exact: true }).click()
      await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
      await expect(page.getByText(/The research text has changed since this reply/)).toHaveCount(0)
      await page.getByRole('button', { name: '3. Write', exact: true }).click()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(exchange.answer.section)
      if (width < 768) {
        const saveBounds = await page.getByLabel('Save and navigate', { exact: true }).boundingBox()
        const navBounds = await page.getByRole('navigation', { name: 'Main navigation', exact: true }).boundingBox()
        expect(saveBounds).not.toBeNull()
        expect(navBounds).not.toBeNull()
        expect(saveBounds!.y + saveBounds!.height).toBeLessThanOrEqual(navBounds!.y + 1)
      }
      await page.screenshot({ path: testInfo.outputPath('write-workspace.png'), fullPage: true })
      await page.getByRole('button', { name: '1. Source', exact: true }).click()
      await page.getByRole('textbox', { name: 'Your notes and selected source content', exact: true }).fill('Edited source notes; the original remains linked to saved research.')
      await page.getByRole('button', { name: '3. Write', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Add section to explanation', exact: true })).toBeDisabled()
      await page.getByRole('button', { name: 'Restore linked passage in source notes', exact: true }).click()
      await expect(page.getByRole('alert').filter({ hasText: 'Your source notes changed' })).toHaveCount(0)
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
