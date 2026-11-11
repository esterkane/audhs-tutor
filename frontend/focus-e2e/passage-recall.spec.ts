import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { API, expectOk, endOpenSession } from '../e2e/helpers'

// Fixture-only clock advancement. Never open a configured application database.
test('explicit prediction enrollment, unprompted recall and clean-browser recovery', async ({
  page,
  request,
  browser,
  baseURL,
}) => {
  const db = process.env.AUDHS_RECALL_FIXTURE_DB
  test.skip(!db, 'Requires the disposable delayed-recall browser fixture')
  if (!db?.match(/^\/tmp\/audhs-c2-browser-[\w-]+\/synthetic\.db$/))
    throw new Error('Disposable browser fixture required')
  await endOpenSession(request)
  const title = 'Synthetic delayed recall of permissions'
  const passage = 'A table privilege permits SELECT. A policy may restrict visible rows.'
  const question = 'What happens when the role has SELECT but no row passes the policy?'
  const prediction = 'I predict an empty result.'
  const answer = 'SELECT succeeds and returns zero visible rows.'
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
  let posted = 0
  page.on('request', (req) => {
    if (req.url().endsWith('/reading-predictions') && req.method() === 'POST') posted++
  })
  await page.goto('/session')
  await page.getByLabel('Your prediction (optional)').fill(prediction)
  await page.getByRole('button', { name: 'Save prediction and read', exact: true }).click()
  await page.getByLabel('How did your prediction compare?').selectOption('confirmed')
  const enroll = page.getByRole('button', { name: 'Save prediction for later recall', exact: true })
  await expect(enroll).toBeEnabled()
  expect(posted).toBe(0)
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/reading-predictions') && r.request().method() === 'POST',
  )
  await enroll.click()
  const res = await saved
  await expectOk(res)
  expect(posted).toBe(1)
  expect(Object.keys(res.request().postDataJSON()).sort()).toEqual([
    'draft_id',
    'learning_object_version',
    'prediction',
    'question_id',
  ])
  const receipt = await res.json()
  expect(await (await request.get(API + '/api/reading-predictions/due')).json()).toBeNull()
  const second = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 } })
  try {
    const recall = await second.newPage()
    const urls: string[] = []
    recall.on('request', (r) => urls.push(r.url()))
    await recall.goto('/review?practice=passage')
    await expect(recall.getByText(/No passage recall is due/)).toBeVisible()
    execFileSync('python3', [
      '-c',
      "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); row=db.execute(\"UPDATE reading_prediction SET due_at=created_at WHERE id=?\",(sys.argv[2],)); assert row.rowcount==1; db.commit()",
      db,
      receipt.id,
    ])
    await recall.getByRole('button', { name: 'Check due passages' }).press('Enter')
    await expect(recall.getByLabel('Your recall answer')).toHaveAccessibleDescription(question)
    const competing = await second.newPage()
    await competing.goto('/review?practice=passage')
    await competing.getByLabel('Your recall answer').fill('Different response from another tab.')
    await expect(recall.getByText(question, { exact: true })).toBeVisible()
    await expect(recall.getByText(prediction, { exact: true })).toHaveCount(0)
    await expect(recall.getByText(passage, { exact: true })).toHaveCount(0)
    await recall.getByLabel('Your recall answer').fill(answer)
    await recall.reload()
    await expect(recall.getByLabel('Your recall answer')).toHaveValue(answer)
    expect(urls.some((url) => url.includes('latest-recall'))).toBe(false)
    await recall.getByRole('button', { name: 'Save recall and compare' }).press('Enter')
    await expect(recall.getByRole('heading', { name: title, exact: true })).toBeFocused()
    expect(await recall.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    await competing.getByRole('button', { name: 'Save recall and compare' }).press('Enter')
    await expect(competing.getByRole('alert')).toBeVisible()
    await expect(competing.getByLabel('Your recall answer')).toHaveValue(
      'Different response from another tab.',
    )
    await competing.getByRole('button', { name: 'Refresh due passages' }).press('Enter')
    await expect(competing.getByText(/No passage recall is due/)).toBeVisible()
    await competing.getByRole('button', { name: 'View last saved recall' }).press('Enter')
    await expect(competing.getByText(answer, { exact: true })).toBeVisible()
    for (const text of [prediction, passage, answer])
      await expect(recall.getByText(text, { exact: true })).toBeVisible()
  } finally {
    await second.close()
  }
  const third = await browser.newContext({ baseURL })
  try {
    const history = await third.newPage()
    await history.goto('/review?practice=passage')
    await expect(history.getByText(/No passage recall is due/)).toBeVisible()
    await history.getByRole('button', { name: 'View last saved recall' }).click()
    for (const text of [prediction, passage, answer])
      await expect(history.getByText(text, { exact: true })).toBeVisible()
  } finally {
    await third.close()
    await endOpenSession(request)
  }
})
