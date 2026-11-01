import { expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const width of [1280, 390]) {
  test(`authoring setup delay preserves writing and gates tutor requests at ${width}`, async ({ page, request }) => {
    const source = "In Python, strings are immutable. text = 'go'; result = text * 1."
    const created = await request.post(`${API}/api/knowledge-material/drafts`, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: { title: 'Synthetic delayed setup', notes: source, workflow_step: 'research', research: {
        passage: source, topic: 'Python repetition', current: 0,
        questions: [{ id: 'q', prompt: 'Does immutability guarantee a new object? Distinguish == and is.', findings: 'Earlier findings.' }],
      } },
    })
    await expectOk(created)
    const draft = await created.json()
    let releaseSetup!: () => void
    const setupGate = new Promise<void>(resolve => { releaseSetup = resolve })
    await page.route('**/api/authoring/setup', async route => {
      await setupGate
      await route.continue()
    })
    let tutorRequests = 0
    page.on('request', req => { if (req.url().endsWith(`/drafts/${draft.id}/research-tutor`)) tutorRequests++ })
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`/curriculum?draft=${draft.id}`)
      await page.locator('summary').filter({ hasText: 'Ask the local tutor (optional)' }).click()
      const draftButton = page.getByRole('button', { name: 'Draft one section locally', exact: true })
      await expect(draftButton).toBeDisabled()
      await expect(page.getByRole('button', { name: 'Discuss my findings locally', exact: true })).toBeDisabled()
      await expect(page.getByText(/Authoring setup is loading or unavailable/)).toBeVisible()
      const findings = page.getByRole('textbox', { name: 'My findings', exact: true })
      await findings.fill('Check equality separately from identity; my new findings are preserved.')
      const save = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}`) && r.request().method() === 'PUT')
      await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
      await expectOk(await save)
      expect(tutorRequests).toBe(0)
      releaseSetup()
      await expect(draftButton).toBeEnabled()
      const reply = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}/research-tutor`))
      await draftButton.click()
      const result = await reply
      await expectOk(result)
      const saved = await result.json()
      const question = saved.payload.authoring.research.questions[0]
      expect(question.findings).toBe('Check equality separately from identity; my new findings are preserved.')
      expect(question.tutor_exchanges[0].reference).toBe('python.string-identity.v1')
      expect(question.tutor_exchanges[0].model_call_id).toBeNull()
      expect(tutorRequests).toBe(1)
      await page.reload()
      await expect(page.getByRole('textbox', { name: 'My findings', exact: true })).toHaveValue(question.findings)
      await expect(page.getByRole('alert').filter({ hasText: 'Authoring settings could not load' })).toHaveCount(0)
    } finally {
      releaseSetup()
    }
  })
}
