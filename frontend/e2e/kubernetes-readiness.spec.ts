import { test, expect } from '@playwright/test'
import { API, expectOk } from './helpers'

test('download the readiness lab and turn saved Kubernetes observations into an editable lesson draft', async ({
  page,
  request,
}) => {
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Kubernetes', exact: true }).click()
  const instructions = page.getByRole('link', { name: 'Download the exercise instructions' })
  const download = page.waitForEvent('download')
  await instructions.click()
  expect((await download).suggestedFilename()).toBe('audhs-readiness-lab.md')
  const guide = await request.get((await instructions.getAttribute('href')) ?? '')
  expect(await guide.text()).toContain('Transfer check from a client Pod')
  const manifest = await request.get(
    (await page
      .getByRole('link', { name: 'Download the Deployment and Service manifest' })
      .getAttribute('href')) ?? '',
  )
  expect(await manifest.text()).toContain('readinessProbe:')
  const evidence =
    'Ready → unready → ready. Endpoint readiness followed. Restarts stayed at 0. The new client Service request succeeded, failed, then succeeded. The server still answered inside the unready Pod.'
  const reflection =
    'The server process can answer locally while its endpoint is ineligible for ordinary Service routing.'
  await page
    .getByLabel('My project notes')
    .fill('Prediction: I expect the unready server to stop answering locally.')
  await page.getByLabel('Test evidence and observed results').fill(evidence)
  await page.getByLabel('What I can explain and what remains uncertain').fill(reflection)
  await page.getByRole('button', { name: 'Submit evidence for review' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'does not certify mastery' })).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Test evidence and observed results')).toHaveValue(evidence)
  const skills = await (await request.get(API + '/api/skills')).json()
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/knowledge-material/drafts') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Create lesson draft from saved findings' }).click()
  const res = await saved
  await expectOk(res)
  const draft = await res.json()
  expect(draft.payload.authoring.focus_topic).toBe('kubernetes')
  expect(draft.payload.authoring.notes).toBe(
    'My test evidence\n' + evidence + '\n\nMy reflection\n' + reflection,
  )
  expect(await (await request.get(API + '/api/skills')).json()).toEqual(skills)
})
