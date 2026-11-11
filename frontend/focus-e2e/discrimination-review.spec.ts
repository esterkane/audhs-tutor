import { expect, test } from '@playwright/test'
import { API, expectOk, endOpenSession } from '../e2e/helpers'

test('rate an explicitly enrolled pair of authored discrimination cases', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await endOpenSession(request)
  const title = 'Synthetic scheduled comparison ' + crypto.randomUUID()
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
  await page.getByLabel('Add these two cases to my review queue on activation').check()
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
        index: session.plan.findIndex((b: { type: string }) => b.type === 'interleaved_review'),
      },
    }),
  )

  const due = await request.get(API + '/api/review/due?session_id=' + session.id)
  await expectOk(due)
  const cards = (await due.json()).items.filter((i: { skill_id: string }) => i.skill_id === skill.id)
  expect(cards).toHaveLength(2)
  expect(cards[0].paired_next_id).toBe(cards[1].item_id)
  await page.goto('/review')
  for (const card of cards) {
    await expect(page.getByText(card.question, { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Show answer', exact: true }).click()
    await expect(page.getByText(card.reveal, { exact: true })).toBeVisible()
    const rating = page.waitForResponse(
      (r) => r.url().endsWith('/review/' + card.item_id) && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: /^Good/ }).click()
    await expectOk(await rating)
  }
  await endOpenSession(request)
})
