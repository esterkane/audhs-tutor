import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) test(`authored material to resumed reading, feedback and saved recap ${width}`, async ({ page, request }) => {
  await endOpenSession(request)
  const title = `Synthetic reading lesson ${width}`
  try {
    const response = await request.post(`${API}/api/knowledge-material/drafts`, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: { title, domain: 'programming', notes: 'Personal synthetic notes about Python strings.',
        objective: 'Predict string repetition without changing the original string.',
        explanation: "For text = 'go', text * 2 produces 'gogo'. The original text stays 'go'.",
        worked_example: "For text = 'a', text * 3 produces 'aaa'; text remains 'a'.",
        question: "For text = 'b', what does text * 2 produce? Does text change?",
        criteria: ['Produces bb.', 'Original text stays b.'], workflow_step: 'review' },
    })
    await expectOk(response)
    const draft = await response.json()
    await page.setViewportSize({ width, height: 900 })
    let generations = 0
    page.on('request', r => { if (/tutor\/(stream|study)/.test(r.url()) && r.method() === 'POST') generations++ })
    await page.goto(`/curriculum?draft=${draft.id}`)
    const published = page.waitForResponse(r => r.url().endsWith(`/drafts/${draft.id}/publish`) && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
    await expectOk(await published)
    const skills = (await (await request.get(`${API}/api/skills`)).json()).skills
    const skill = skills.find((s: { title: string }) => s.title === title)
    expect(skill).toBeTruthy()
    await page.goto(`/?lesson=${encodeURIComponent(skill.id)}`)
    const started = page.waitForResponse(r => r.url().endsWith('/api/sessions') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
    const confirmedStart = await started
    await expectOk(confirmedStart)
    const current = await confirmedStart.json()
    await expect(page).toHaveURL(/\/session$/)
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: {
      session_id: current.id, index: current.plan.findIndex((b: { type: string }) => b.type === 'new_material'),
    } }))
    await page.goto('/session')
    const path = page.getByRole('navigation', { name: 'Learning path' })
    const readingPath = page.getByRole('navigation', { name: 'Reading location' })
    await expect(path).toContainText(title)
    await expect(readingPath).toContainText(title)
    await expect(page.getByText('Reading time: about 1 min (estimate)', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Next section', exact: true }).click()
    await expect(readingPath).toContainText('Section 2 of 2: A worked example')
    await page.getByLabel('Your notes for this section (optional)').fill('Keep my worked-example note.')
    await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect(readingPath).toContainText('Section 2 of 2: A worked example')
    await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue('Keep my worked-example note.')
    await page.getByRole('button', { name: 'Try this lesson', exact: true }).click()
    await page.getByLabel('Your answer', { exact: true }).fill("I don't know")
    const checked = page.waitForResponse(r => r.url().endsWith('/api/assess/attempt'))
    await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
    await expectOk(await checked)
    await expect(path).toContainText('Understanding check')
    await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Revisit the explanation', exact: true }).click()
    await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue('Keep my worked-example note.')
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    expect(generations).toBe(0)
    await page.goto('/recap')
    await page.getByLabel('One line for next time (optional)').fill('Resume the worked example next time.')
    await page.getByRole('button', { name: 'Save and finish session', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Session saved', exact: true })).toBeVisible()
  } finally { await endOpenSession(request) }
})
