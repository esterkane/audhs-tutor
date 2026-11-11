import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from '../e2e/helpers'

test('author and replay a variable trace with original predictions and a changed-condition question', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await endOpenSession(request)
  const title = 'Synthetic state walkthrough'
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
  const author = page.locator('summary').filter({ hasText: 'Variable walkthrough (optional)' })
  await author.press('Enter')
  await page.getByLabel('Add a variable walkthrough').press('Space')
  await page.getByLabel('Variable name').fill('visible_rows')
  await page.getByLabel('Starting value').fill('0')
  await page.getByLabel('Action at step 1').fill('A visible row is added to the count.')
  await page.getByLabel('Value after step 1').fill('1')
  await page.getByLabel('Action at step 2').fill('A hidden row is skipped.')
  await page.getByLabel('Value after step 2').fill('1')
  await page
    .getByLabel('Transfer question with one changed condition')
    .fill('If the second row were visible, what would the count be?')
  await page.getByLabel('Author’s answer to the transfer question').fill('2')
  const saving = page.waitForResponse(
    (r) => r.url().endsWith('/drafts/' + draft.id) && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expectOk(await saving)
  await page.reload()
  await author.press('Enter')
  await expect(page.getByLabel('Action at step 2')).toHaveValue('A hidden row is skipped.')
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
  const open = () => page.locator('summary').filter({ hasText: 'Trace a changing value' }).press('Enter')
  await open()
  const trace = page.getByRole('region', { name: 'Variable walkthrough' })
  const prediction = trace.getByLabel('Your prediction (optional)')
  await expect(trace).toContainText('Previous value: 0')
  await expect(trace).not.toContainText('Value changed:')
  const writes: string[] = []
  page.on('request', (r) => {
    if (r.method() === 'POST') writes.push(r.url())
  })
  await prediction.fill('probably 3')
  await trace.getByRole('button', { name: 'Reveal next value' }).press('Enter')
  await expect(trace).toContainText('Value changed: 0 → 1')
  await trace.getByRole('button', { name: 'Next step' }).press('Enter')
  await expect(trace.getByRole('heading')).toBeFocused()
  await prediction.fill('still 1')
  await page.reload()
  await open()
  await expect(prediction).toHaveValue('still 1')
  await trace.getByRole('button', { name: 'Reveal next value' }).press('Enter')
  await expect(trace).toContainText('Value stayed the same: 1 → 1')
  await trace.getByRole('button', { name: 'Try the transfer question' }).press('Enter')
  await expect(trace).not.toContainText('Author’s answer:')
  await prediction.fill('2 rows')
  await trace.getByRole('button', { name: 'Show author’s answer' }).press('Enter')
  await expect(trace).toContainText('Author’s answer: 2')
  await trace.getByRole('button', { name: 'Previous step' }).press('Enter')
  await expect(trace).toContainText('Your original prediction: still 1')
  await trace.getByRole('button', { name: 'Replay from the start' }).press('Enter')
  await expect(trace).toContainText('Your original prediction: probably 3')
  await expect(trace).toContainText('Value changed: 0 → 1')
  expect(writes.filter((u) => /assess|mastery|tutor|prediction/.test(u))).toEqual([])
  await endOpenSession(request)
})
