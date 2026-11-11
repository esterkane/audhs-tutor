import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test('turn saved Supabase findings into a personal lesson and resume reading', async ({ page, request }) => {
  await endOpenSession(request)
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Supabase', exact: true }).click()
  const evidence = 'In my fixture the support role read zero rows under the policy.'
  const reflection = 'I still need to distinguish visibility from table grants.'
  await page.getByLabel('My project notes').fill('Private scratch, excluded from transfer.')
  await page.getByLabel('Test evidence and observed results').fill(evidence)
  await page.getByLabel('What I can explain and what remains uncertain').fill(reflection)
  const create = page.getByRole('button', { name: 'Create lesson draft from saved findings' })
  await expect(create).toBeDisabled()
  await page.getByRole('button', { name: 'Save project notes' }).click()
  await expect(create).toBeEnabled()
  const projects = await (await request.get(API + '/api/projects')).json()
  const skills = await (await request.get(API + '/api/skills')).json()
  const creating = page.waitForResponse(
    (r) => r.url().endsWith('/knowledge-material/drafts') && r.request().method() === 'POST',
  )
  await create.click()
  const res = await creating
  await expectOk(res)
  const draft = await res.json()
  expect(draft.payload.authoring.notes).toBe(
    'My test evidence\n' + evidence + '\n\nMy reflection\n' + reflection,
  )
  expect(draft.payload.authoring.focus_topic).toBe('supabase')
  expect(await (await request.get(API + '/api/skills')).json()).toEqual(skills)
  await page
    .getByLabel('Learning objective', { exact: true })
    .fill('Separate row visibility from permissions.')
  const explanation = 'Rows visible to an application depend on the policy that applies to its role.'
  await page.getByLabel('Explanation', { exact: true }).fill(explanation)
  await page.getByLabel('Worked example', { exact: true }).fill('Our application role saw no matching rows.')
  await page
    .getByLabel('Application question', { exact: true })
    .fill('What can you infer from zero visible rows?')
  await page.getByLabel(/Success criteria/).fill('Distinguishes visibility from missing privileges.')
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByRole('article', { name: 'Knowledge material preview' })).toContainText(explanation)
  const writing = page.waitForResponse(
    (r) => r.url().endsWith('/drafts/' + draft.id) && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save knowledge material' }).click()
  await expectOk(await writing)
  const accepting = page.waitForResponse(
    (r) => r.url().endsWith('/publish') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  await expectOk(await accepting)
  const skill = (await (await request.get(API + '/api/skills')).json()).skills.find(
    (s: { title: string }) => s.title === draft.payload.authoring.title,
  )
  await page.goto('/?lesson=' + skill.id)
  const starting = page.waitForResponse(
    (r) => r.url().endsWith('/api/sessions') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
  const session = await (await starting).json()
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
  await expect(page.getByText(explanation, { exact: true }).first()).toBeVisible()
  await page.getByLabel('Your notes for this section (optional)').fill('Continue with grants.')
  await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
  await page.getByRole('button', { name: 'Continue', exact: true }).click()
  await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue('Continue with grants.')
  expect(await (await request.get(API + '/api/projects')).json()).toEqual(projects)
  await endOpenSession(request)
})
