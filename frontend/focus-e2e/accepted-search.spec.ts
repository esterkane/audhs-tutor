import { expect, test } from '@playwright/test'
import { API, expectOk } from '../e2e/helpers'

test('search finds a worked example across activation and follows the latest accepted revision', async ({
  page,
  request,
}) => {
  const body = {
    title: 'Synthetic visibility lesson',
    focus_topic: 'postgresql',
    domain: 'programming',
    notes: 'Personal note about grants.',
    objective: 'Separate privileges from visibility.',
    explanation: 'Grants permit the operation.',
    worked_example: 'Copper ibis rows remain hidden.',
    question: 'What does SELECT permit?',
    criteria: ['Can read table.'],
    workflow_step: 'review',
  }
  const created = await request.post(API + '/api/knowledge-material/drafts', {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    data: body,
  })
  await expectOk(created)
  const draft = await created.json()
  const material = page.getByRole('region', { name: 'My material' })
  const search = async (q: string) => {
    await page.goto('/library?q=' + encodeURIComponent(q))
    await expect(material.getByText('Searching your material…')).toHaveCount(0)
  }
  await search('Copper ibis')
  await expect(material.getByRole('link', { name: body.title })).toHaveAttribute(
    'href',
    '/curriculum?draft=' + draft.id,
  )
  const discardedResponse = await request.post(API + '/api/knowledge-material/drafts', {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    data: { ...body, title: 'Retired scratchpad', worked_example: 'An unrelated retired example.' },
  })
  await expectOk(discardedResponse)
  const discarded = await discardedResponse.json()
  await expectOk(
    await request.post(API + '/api/curriculum/drafts/' + discarded.id + '/reject', {
      data: { expected_version: discarded.version },
    }),
  )
  await search('Retired scratchpad')
  await expect(material.getByText(/Discarded draft/)).toBeVisible()
  await expect(material.getByRole('link', { name: 'Retired scratchpad' })).toHaveAttribute(
    'href',
    '/curriculum?draft=' + discarded.id,
  )
  await search(draft.payload.authoring.request_id)
  await expect(material.getByText('No material matched.')).toBeVisible()
  const published = await request.post(API + '/api/curriculum/drafts/' + draft.id + '/publish', {
    data: { expected_version: draft.version },
  })
  await expectOk(published)
  const active = (await published.json()).draft
  const skills = (await (await request.get(API + '/api/skills')).json()).skills
  const skill = skills.find((s: { title: string }) => s.title === body.title)
  const launch = '/?lesson=' + skill.id
  await search('Copper ibis')
  await expect(material.getByRole('link', { name: body.title })).toHaveAttribute('href', launch)
  const revisionR = await request.post(API + '/api/knowledge-material/drafts/' + draft.id + '/revise', {
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    data: { expected_version: active.version },
  })
  await expectOk(revisionR)
  const revision = await revisionR.json()
  const changedR = await request.put(API + '/api/knowledge-material/drafts/' + revision.id, {
    data: { ...body, worked_example: 'Silver egret rows remain hidden.', expected_version: revision.version },
  })
  await expectOk(changedR)
  const changed = await changedR.json()
  await search('Silver egret')
  await expect(material.getByRole('link', { name: body.title })).toHaveAttribute(
    'href',
    '/curriculum?draft=' + revision.id,
  )
  await search('Copper ibis')
  await expect(material.getByRole('link', { name: body.title })).toHaveAttribute('href', launch)
  await expectOk(
    await request.post(API + '/api/curriculum/drafts/' + revision.id + '/publish', {
      data: { expected_version: changed.version },
    }),
  )
  await search('Copper ibis')
  await expect(material.getByText('No material matched.')).toBeVisible()
  await search('Silver egret')
  const lesson = material.getByRole('link', { name: body.title })
  await expect(lesson).toHaveAttribute('href', launch)
  await lesson.press('Enter')
  await expect(page.getByRole('button', { name: 'Start this lesson' })).toBeVisible()
})
