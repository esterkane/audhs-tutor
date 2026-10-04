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
  const duplicateKeys: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error' && message.text().includes('same key')) duplicateKeys.push(message.text())
  })
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
  await page.getByRole('button', { name: /^Continue$/ }).click()
  await expect(page.getByRole('heading', { name: 'Learning goal' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Give me a hint' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Explain the idea first' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to learning goal' })).toBeVisible()
  await page.getByText('Rate this question', { exact: true }).click()
  await page
    .getByLabel('Your explanation (optional)', { exact: true })
    .fill('Keep this question feedback draft')
  const choices = page.getByRole('group', { name: 'Your answer' })
  if (await choices.isVisible()) await choices.getByRole('button').first().click()
  else await page.getByLabel('Your answer', { exact: true }).fill('My attempt')
  await expect(page.getByRole('button', { name: 'Check my answer' })).toBeEnabled()
  await expect(page.getByLabel('Your explanation (optional)', { exact: true })).toHaveValue(
    'Keep this question feedback draft',
  )
  await expect(page.getByRole('button', { name: 'Give me a hint' })).toHaveCount(1)
  await page.route('**/api/tutor/stream', async (route) => {
    const done = {
      turn_id: 'hint-source',
      sources: [{ chunk_id: 'hint-chunk', citation: '[Example hint source]', cited: true, flagged: [] }],
      dropped: [],
      text: 'Consider the units in the example.',
    }
    await route.fulfill({
      contentType: 'text/event-stream',
      body: `event: meta\ndata: ${JSON.stringify({ turn_id: 'hint-source' })}\n\nevent: token\ndata: ${JSON.stringify({ text: done.text })}\n\nevent: done\ndata: ${JSON.stringify(done)}\n\n`,
    })
  })
  await page.route('**/api/curriculum/chunks/hint-chunk', (route) =>
    route.fulfill({
      json: {
        chunk_id: 'hint-chunk',
        citation: '[Example hint source]',
        text: 'Compare both quantities using the same units.',
        document_title: 'Synthetic source',
        source_type: 'text',
        trust_tier: 2,
        uri: '/materials/example.txt',
        open_url: null,
      },
    }),
  )
  await page.getByRole('button', { name: 'Give me a hint' }).click()
  await page.getByText('Sources for this explanation', { exact: true }).click()
  const citation = page.getByRole('button', { name: '[Example hint source]', exact: true })
  await citation.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Compare both quantities using the same units.')).toBeVisible()
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await expect(citation).toBeFocused()
  await expect(page.getByText('Confidence (optional)')).toBeVisible()
  await expect(page.getByRole('group', { name: /How sure are you/ })).not.toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('session-assessment.png'), fullPage: true })
  await page.getByRole('button', { name: 'Ask me again later' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Ask me later list' })).toBeVisible()
  await page.getByRole('button', { name: 'Change topic' }).click()
  await page.getByText('Change new-session topic', { exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Knowledge area' })).toBeVisible()
  expect(await currentSession(request)).toBeNull()
  const ended = await (await request.get(`${API}/api/sessions/${session.id}`)).json()
  expect(ended.energy_after).toBeNull()
  await page.getByText('Saved material · clear / ask me later', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Revisit this lesson' })).toBeVisible()
  expect(duplicateKeys).toEqual([])
})
