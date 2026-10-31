import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const [language, width] of [
  ['en', 1280],
  ['de', 390],
] as const) {
  test(`vector comparison research stays editable after reload in ${language} at ${width}`, async ({
    page,
    request,
  }) => {
    const preferences = (await (await request.get(`${API}/api/preferences`)).json()).values
    try {
      for (const [key, value] of [
        ['tutor.persona', 'kangaroo'],
        ['tutor.response_language', language],
      ])
        await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value } }))
      const source =
        language === 'de'
          ? 'Vektoren:\r\nq=[1,0]\r\nA=[1,0]\r\nB=[10,1]'
          : 'Vectors:\nq=[1,0]\nA=[1,0]\nB=[10,1]'
      const uploaded = await request.post(`${API}/api/knowledge-material/uploads`, {
        headers: { 'Content-Type': 'application/octet-stream', 'X-Filename': 'synthetic-vectors.txt' },
        data: Buffer.from(source),
      })
      await expectOk(uploaded)
      const upload = await uploaded.json()
      expect(upload.text.trim()).toBe(source.replaceAll('\r\n', '\n').trim())
      const response = await request.post(`${API}/api/knowledge-material/drafts`, {
        headers: { 'Idempotency-Key': crypto.randomUUID() },
        data: {
          title: `Synthetic reference research ${language}`,
          notes: source,
          upload_id: upload.document_id,
          workflow_step: 'research',
          research: {
            passage: source,
            topic: 'Vector similarity',
            current: 0,
            questions: [
              {
                id: 'q',
                prompt:
                  language === 'de'
                    ? 'Vergleiche Skalarprodukt und Kosinusähnlichkeit für Anfragevektor `q` mit Kandidaten `A` und `B`.'
                    : 'Compare dot product and cosine similarity for query `q` with candidates `A` and `B`.',
                findings: 'I think B has the larger cosine because it is longer.',
              },
            ],
          },
        },
      })
      await expectOk(response)
      const draft = await response.json()
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`/curriculum?draft=${draft.id}`)
      await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
      const started = performance.now()
      const reply = page.waitForResponse((r) => r.url().endsWith(`/drafts/${draft.id}/research-tutor`))
      await page.getByRole('button', { name: 'Draft one section locally', exact: true }).click()
      const saved = await (await reply).json()
      const exchange = saved.payload.authoring.research.questions[0].tutor_exchanges[0]
      console.log(JSON.stringify({ language, checked_reply_ms: Math.round(performance.now() - started) }))
      expect(exchange.calculation).toBe('vector.dot-cosine.v1')
      expect(exchange.model_call_id).toBeNull()
      expect(exchange.answer.source_quotes).toEqual([source])
      expect(exchange.answer.section).toContain('0.99503719021')
      expect(exchange.answer.section).toContain('`B` > `A`')
      expect(exchange.answer.section).toContain('`A` > `B`')
      expect(exchange.answer.section).toContain(language === 'de' ? 'Skalarprodukt' : 'dot product')
      await expect(page.getByText(/Saved vector calculation — provenance not verified/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Ask for another reply', exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: 'Use tutor draft in my section', exact: true }).click()
      await page.getByRole('button', { name: '3. Write', exact: true }).click()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(
        exchange.answer.section,
      )
      await page.getByRole('button', { name: 'Add section to explanation', exact: true }).click()
      const write = page.waitForResponse(
        (r) => r.url().endsWith(`/drafts/${draft.id}`) && r.request().method() === 'PUT',
      )
      await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
      await expectOk(await write)
      await page.reload()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toBeEnabled()
      await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(
        exchange.answer.section,
      )
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
