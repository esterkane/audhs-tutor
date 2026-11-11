import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from '../e2e/helpers'

test('recall selected terms silently from accepted reading', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await endOpenSession(request)
  const title = 'Private key term practice'
  const created = await request.post(API + '/api/knowledge-material/drafts', {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    data: {
      title,
      focus_topic: 'postgresql',
      domain: 'programming',
      notes: 'Source notes about visibility.',
      explanation: 'A role can see rows that pass the policy.',
      worked_example: 'The role sees only its own orders.',
      objective: 'Explain row visibility.',
      question: 'Which orders can this role see?',
      criteria: ['Explain the policy.'],
      workflow_step: 'review',
    },
  })
  await expectOk(created)
  const draft = await created.json()
  await page.goto('/curriculum?draft=' + draft.id)
  const published = page.waitForResponse(
    (r) => r.url().endsWith('/publish') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  await expectOk(await published)
  const skill = (await (await request.get(API + '/api/skills')).json()).skills.find(
    (s: { title: string }) => s.title === title,
  )
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
  await page.goto('/session')
  await page.getByRole('button', { name: 'Read without predicting' }).click()
  const writes: string[] = []
  page.on('request', (r) => {
    if (r.method() !== 'GET') writes.push(r.url())
  })
  await page.getByRole('button', { name: 'Practise key terms' }).press('Enter')
  const terms = page.getByLabel('Terms to practise (one per line)')
  await terms.fill('role\nrows\ninvented')
  await page.getByRole('button', { name: 'Hide passage and recall' }).press('Enter')
  await expect(page.getByRole('alert')).toContainText('Copy each exactly')
  await terms.fill('role\nrows\npolicy')
  await page.getByRole('button', { name: 'Hide passage and recall' }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Recall your terms' })).toBeFocused()
  await expect(page.getByText('A role can see rows that pass the policy.', { exact: true })).toBeHidden()
  await page.getByLabel('What I recall (optional)').fill('role and policy')
  await page.getByRole('button', { name: 'Show my terms' }).press('Enter')
  const comparison = page.getByRole('region', { name: 'Compare with your terms' })
  await expect(comparison.getByRole('listitem')).toHaveText(['role', 'rows', 'policy'])
  await expect(comparison).toContainText('Your recall: role and policy')
  await page.getByRole('button', { name: 'Recall again' }).press('Enter')
  await expect(page.getByLabel('What I recall (optional)')).toHaveValue('')
  await page.getByRole('button', { name: 'Finish practice' }).press('Enter')
  await expect(page.getByRole('button', { name: 'Practise key terms' })).toBeFocused()
  await expect(page.getByText('A role can see rows that pass the policy.', { exact: true })).toBeVisible()
  expect(
    writes.filter((url) => /voice|audio|models|assessment|mastery|review|predictions/.test(url)),
  ).toEqual([])
  await endOpenSession(request)
})
