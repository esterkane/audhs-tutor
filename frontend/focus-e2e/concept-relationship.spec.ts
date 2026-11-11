import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from '../e2e/helpers'

test('author a relationship and resume a learner-completed link before and after comparison', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await endOpenSession(request)
  const title = 'Synthetic row relationship'
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
  const author = page.locator('summary').filter({ hasText: 'Concept relationship (optional)' })
  await author.press('Enter')
  await page.getByLabel('Add a relationship to practise').press('Space')
  await page.getByLabel('Starting concept').fill('A row policy')
  await page.getByLabel('Linking phrase').fill('restricts the set of')
  await page.getByLabel('Ending concept').fill('visible orders')
  const saving = page.waitForResponse(
    (r) => r.url().endsWith('/drafts/' + draft.id) && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expectOk(await saving)
  await page.reload()
  await author.press('Enter')
  await expect(page.getByLabel('Linking phrase')).toHaveValue('restricts the set of')
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
  const open = () => page.locator('summary').filter({ hasText: 'Connect two concepts' }).press('Enter')
  await open()
  const box = page.getByLabel('Your linking phrase')
  await expect(page.getByText('Authored statement', { exact: true })).toHaveCount(0)
  const writes: string[] = []
  page.on('request', (r) => {
    if (r.method() === 'POST') writes.push(r.url())
  })
  await box.fill('determines which rows become')
  await page.reload()
  await open()
  await expect(box).toHaveValue('determines which rows become')
  await page.getByRole('button', { name: 'Compare my relationship' }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Compare the relationships' })).toBeFocused()
  await expect(page.getByText('A row policy restricts the set of visible orders')).toBeVisible()
  await page.reload()
  await open()
  await expect(page.getByText('A row policy determines which rows become visible orders')).toBeVisible()
  await expect(page.getByText('A row policy restricts the set of visible orders')).toBeVisible()
  const part = page.getByLabel('Part to complete')
  await part.selectOption('target')
  const activity = page.getByRole('region', { name: 'Practise a concept relationship' })
  await expect(activity).not.toContainText('visible orders')
  await page.getByLabel('Your ending concept').fill('orders the role can read')
  await page.reload()
  await open()
  await expect(part).toHaveValue('target')
  await expect(page.getByLabel('Your ending concept')).toHaveValue('orders the role can read')
  await page.getByRole('button', { name: 'Compare my relationship' }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Compare the relationships' })).toBeFocused()
  await expect(activity).toContainText('A row policy restricts the set of orders the role can read')
  await expect(activity).toContainText('A row policy restricts the set of visible orders')
  await part.selectOption('link')
  await expect(activity).toContainText('A row policy determines which rows become visible orders')
  await part.selectOption('target')
  await expect(activity).toContainText('A row policy restricts the set of orders the role can read')
  expect(writes.filter((u) => /assess|mastery|prediction|tutor\//.test(u))).toEqual([])
  await endOpenSession(request)
})
