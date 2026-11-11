import { expect, test } from '@playwright/test'
import { API, expectOk, endOpenSession } from '../e2e/helpers'

test('author, accept, compare, restore and skip on a narrow screen', async ({
  page,
  request,
  browser,
  baseURL,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await endOpenSession(request)
  const title = 'Synthetic separated permissions'
  const passage = 'A table privilege permits SELECT. A policy may restrict visible rows.'
  const question = 'What happens when the role has SELECT but no row passes the policy?'
  const caseA = 'The role has a SELECT grant, but a policy hides the row.'
  const caseB = 'The role lacks the required table SELECT grant.'
  const cue = 'Which table privilege does each role have before a row policy applies?'
  const why = 'Case B fails its table privilege check before row policies apply.'
  const draftResponse = await request.post(API + '/api/knowledge-material/drafts', {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    data: {
      title,
      focus_topic: 'postgresql',
      domain: 'programming',
      objective: 'Distinguish privilege from visibility.',
      notes: 'Synthetic database permission notes.',
      explanation: passage,
      explanation_prequestion: question,
      worked_example: 'An application role sees only the matching rows.',
      question: 'What does the table privilege permit?',
      criteria: ['SELECT is a separate privilege.'],
      workflow_step: 'review',
    },
  })
  await expectOk(draftResponse)
  const draft = await draftResponse.json()
  await page.goto('/curriculum?draft=' + draft.id)
  await page.locator('summary').filter({ hasText: 'Compare two cases (optional)' }).press('Enter')
  await page.getByLabel('Include a case comparison').check()
  await page.getByLabel('Case A', { exact: true }).fill(caseA)
  await page.getByLabel('Case B', { exact: true }).fill(caseB)
  await page.getByLabel('What should the learner compare? (optional)').fill(cue)
  await page.getByLabel('Which case fails?').selectOption('b')
  await page.getByLabel('Why does that case fail?').fill(why)
  const saving = page.waitForResponse(
    (r) => r.url().endsWith('/drafts/' + draft.id) && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expectOk(await saving)
  await page.reload()
  await page.locator('summary').filter({ hasText: 'Compare two cases (optional)' }).press('Enter')
  await expect(page.getByLabel('Why does that case fail?')).toHaveValue(why)
  const published = page.waitForResponse(
    (r) => r.url().endsWith('/publish') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  await expectOk(await published)
  const skills = (await (await request.get(API + '/api/skills')).json()).skills
  const skill = skills.find((s: { title: string }) => s.title === title)
  await page.goto('/?lesson=' + encodeURIComponent(skill.id))
  const started = page.waitForResponse(
    (r) => r.url().endsWith('/api/sessions') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
  const session = await (await started).json()
  await expectOk(
    await request.post(API + '/api/plan/blocks/start', {
      data: {
        session_id: session.id,
        index: session.plan.findIndex((b: { type: string }) => b.type === 'new_material'),
      },
    }),
  )
  const writes: string[] = []
  page.on('request', (req) => {
    if (req.method() === 'POST') writes.push(req.url())
  })
  await page.goto('/session')
  const open = page.locator('summary').filter({ hasText: 'Compare two cases' })
  await open.press('Enter')
  for (const text of [caseA, caseB]) await expect(page.getByText(text, { exact: true })).toBeVisible()
  await expect(page.getByText(why, { exact: true })).toHaveCount(0)
  const guide = page.locator('summary').filter({ hasText: 'Help me compare the cases' })
  await expect(page.getByText(cue, { exact: true })).not.toBeVisible()
  await guide.press('Enter')
  await expect(page.getByText(cue, { exact: true })).toBeVisible()
  const detailA = 'The role has the table grant.'
  const detailB = 'The required table grant is absent.'
  await page.getByLabel('Relevant detail from Case A (optional)').fill(detailA)
  await page.getByLabel('Relevant detail from Case B (optional)').fill(detailB)
  await expect(page.getByText(why, { exact: true })).toHaveCount(0)
  await page.getByRole('radio', { name: 'Case A' }).check()
  const reasoning = 'I initially suspected the policy denied the command.'
  await page.getByLabel('Why does it fail?').fill(reasoning)
  await page.reload()
  await open.press('Enter')
  await expect(page.getByRole('radio', { name: 'Case A' })).toBeChecked()
  await expect(page.getByLabel('Why does it fail?')).toHaveValue(reasoning)
  await guide.press('Enter')
  await expect(page.getByLabel('Relevant detail from Case A (optional)')).toHaveValue(detailA)
  await expect(page.getByLabel('Relevant detail from Case B (optional)')).toHaveValue(detailB)
  await page.getByRole('button', { name: 'Compare with explanation' }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Compare with the author’s explanation' })).toBeFocused()
  await expect(page.getByText(why, { exact: true })).toBeVisible()
  await expect(page.getByText('Your reasoning: ' + reasoning, { exact: true })).toBeVisible()
  await expect(page.getByText('Your detail from Case A: ' + detailA, { exact: true })).toBeVisible()
  await expect(page.getByText('Your detail from Case B: ' + detailB, { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.reload()
  await open.press('Enter')
  await expect(page.getByText(why, { exact: true })).toBeVisible()
  const storageState = await page.context().storageState()
  for (const origin of storageState.origins)
    origin.localStorage = origin.localStorage.filter((item) => !item.name.startsWith('case-comparison:v1:'))
  const second = await browser.newContext({ baseURL, storageState, viewport: { width: 390, height: 844 } })
  try {
    const other = await second.newPage()
    await other.goto('/session')
    await other.locator('summary').filter({ hasText: 'Compare two cases' }).press('Enter')
    await expect(other.getByText(why, { exact: true })).toHaveCount(0)
    await other.getByRole('radio', { name: 'Case B' }).check()
    await expect(other.getByLabel('Why does it fail? (optional)')).toHaveValue('')
    await other.getByRole('button', { name: 'Compare with explanation' }).press('Enter')
    await expect(other.getByText('Your choice: Case B', { exact: true })).toBeVisible()
    await other.evaluate(() => {
      for (const key of Object.keys(localStorage))
        if (key.startsWith('case-comparison:v1:')) localStorage.removeItem(key)
    })
    await other.reload()
    await other.locator('summary').filter({ hasText: 'Compare two cases' }).press('Enter')
    await other.getByRole('button', { name: 'Skip to explanation' }).press('Enter')
    await expect(other.getByText(why, { exact: true })).toBeVisible()
    await expect(other.getByText(/Your choice:/)).toHaveCount(0)
  } finally {
    await second.close()
    await endOpenSession(request)
  }
  expect(
    writes.filter((url) => /assess|mastery|reading-predictions|tutor\/(stream|study)/.test(url)),
  ).toEqual([])
})
