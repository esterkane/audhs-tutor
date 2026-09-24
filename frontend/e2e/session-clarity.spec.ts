import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, currentSession } from './helpers'

test.beforeEach(async ({ request }) => {
  await endOpenSession(request)
  await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
  await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
})
test.afterEach(async ({ request }) => endOpenSession(request))

test('context, optional confidence, saved labels and stopping without recap', async ({
  page,
  request,
}, testInfo) => {
  const res = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
  await expectOk(res)
  const session = await res.json()
  const ix = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
  await expectOk(
    await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index: ix } }),
  )
  await expectOk(
    await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess' } }),
  )
  await page.goto('/')
  await page.getByRole('button', { name: /^Resume previous session/ }).click()
  await expect(page.getByRole('heading', { name: 'What you are learning' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Give me a hint' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Explain the idea first' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
  const choices = page.getByRole('group', { name: 'Your answer' })
  if (await choices.isVisible()) await choices.getByRole('button').first().click()
  else await page.getByLabel('Your answer', { exact: true }).fill('My attempt')
  await expect(page.getByRole('button', { name: 'Check my answer' })).toBeEnabled()
  await expect(page.getByText('Confidence (optional)')).toBeVisible()
  await expect(page.getByRole('group', { name: /How sure are you/ })).not.toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('session-assessment.png'), fullPage: true })
  await page.getByRole('button', { name: 'Ask me again later' }).click()
  await expect(page.getByRole('status')).toContainText('Ask me later list')
  await page.getByRole('button', { name: 'Change topic' }).click()
  await expect(page.getByRole('combobox', { name: 'Knowledge area' })).toBeVisible()
  expect(await currentSession(request)).toBeNull()
  const ended = await (await request.get(`${API}/api/sessions/${session.id}`)).json()
  expect(ended.energy_after).toBeNull()
  await page.getByText('Saved material · clear / ask me later', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Revisit this lesson' })).toBeVisible()
})
