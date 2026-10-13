import { expect, test } from '@playwright/test'
import axe from 'axe-core'
for (const width of [390, 1280]) test(`private lesson save recovery and review ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  const answer = { id: 'lesson-answer', surface: 'ask', turn_id: 'turn', created_at: '2026-10-13T10:00:00Z', request_text: 'How does preprocessing work?', text: 'Fit on training data. Apply the same transform to held-out data.', request: {}, metadata: {}, session_id: null, skill_id: null, area_id: null, source_check: { sources: [], omitted: 0 } }
  const binding = { schema_version: 'answer-lesson-binding.v1', answer_id: answer.id, question_sha256: 'a'.repeat(64), answer_sha256: 'b'.repeat(64), lineage_sha256: 'c'.repeat(64), source_state_sha256: 'd'.repeat(64) }
  const draft = { id: 'saved-lesson', course: null, section: null, title: 'Training-only preprocessing', status: 'draft', origin: 'answer_derived', version: 1, problems: [], payload: { domain: 'ai_ml', skills: [], learning_objects: [], assessments: [] }, created_at: 'now', updated_at: 'now', published_at: null }
  const requests: { key: string; body: string }[] = []
  let otherWrites = 0
  await page.route('**/api/areas', route => route.fulfill({ json: { areas: [], total_documents: 0, unassigned_documents: 0 } }))
  await page.route('**/api/answers/lesson-answer', route => route.fulfill({ json: answer }))
  await page.route('**/api/lesson-promotions/answers/*/preview', route => route.fulfill({ json: { binding, grounding: 'ungrounded', issues: [], publication_available: false } }))
  await page.route('**/api/lesson-promotions/drafts', route => {
    requests.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! })
    if (requests.length === 1) return route.abort()
    return route.fulfill({ json: { action: 'create_private_draft', draft_id: draft.id, promotion_id: 'promotion', created_version: 1 } })
  })
  await page.route('**/api/lesson-activations/**', route => {
    if (route.request().method() !== 'GET') { otherWrites++; return route.abort() }
    return route.fulfill({ json: { draft_id: draft.id, promotion_id: 'promotion', draft_version: 1, title: draft.title, status: 'draft', command: null, receipt: null, skills: 0, assessments: 0, learning_objects: 0, grounding: 'ungrounded', warnings: [], issues: ['Add lesson content before activation.'] } })
  })
  await page.route('**/api/curriculum/**', route => {
    if (route.request().method() !== 'GET') { otherWrites++; return route.abort() }
    return route.fulfill({ json: route.request().url().includes('/material') ? { courses: [] } : { drafts: [draft] } })
  })
  await page.goto('/ask?answer=lesson-answer')
  const disclosure = page.locator('summary').filter({ hasText: 'Create lesson draft (optional)' })
  await disclosure.focus(); await page.keyboard.press('Enter')
  await expect(page.getByText(/After saving, open the lesson draft to review it/)).toBeVisible()
  await page.getByLabel('Lesson title', { exact: true }).fill(draft.title)
  await page.getByLabel('What should the learner be able to do?').fill('Apply training-only statistics.')
  await page.getByRole('button', { name: 'Use answer as explanation' }).click()
  await page.getByRole('textbox', { name: 'Worked example', exact: true }).fill('Training ages 20 and 40 have median 30.')
  await page.getByLabel('Application question', { exact: true }).fill('Which median fills held-out ages?')
  await page.getByLabel('Grading criteria').fill('Use training ages only\nApply the same median')
  await page.reload(); await disclosure.click()
  await expect(page.getByRole('textbox', { name: 'Worked example', exact: true })).toHaveValue('Training ages 20 and 40 have median 30.')
  await page.getByRole('button', { name: 'Save private lesson draft', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Retry previous request', exact: true })).toBeVisible()
  await page.getByLabel('Lesson title', { exact: true }).fill('Later unsent edit')
  await page.getByRole('button', { name: 'Retry previous request', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Open saved lesson draft' })).toBeVisible()
  expect(requests).toHaveLength(2); expect(requests[1]).toEqual(requests[0])
  expect(JSON.parse(requests[1].body).title).toBe(draft.title)
  await expect(page.getByLabel('Lesson title', { exact: true })).toHaveValue('Later unsent edit')
  await page.addScriptTag({ content: axe.source })
  expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: `/tmp/audhs-ask-lesson-${width}.png`, fullPage: true })
  await page.getByRole('link', { name: 'Open saved lesson draft' }).focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: draft.title, exact: true })).toBeFocused()
  await expect(page.getByText('Add lesson content before activation.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Activate private lessons', exact: true })).toHaveCount(0)
  await page.reload()
  await expect(page.getByRole('heading', { name: draft.title, exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Back to drafts' }).click()
  await page.goBack()
  await expect(page.getByRole('heading', { name: draft.title, exact: true })).toBeVisible()
  expect(otherWrites).toBe(0)
})
