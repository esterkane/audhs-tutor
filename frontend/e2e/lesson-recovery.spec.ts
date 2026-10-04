import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test.beforeEach(async ({ request }) => {
  await endOpenSession(request)
  for (const key of ['goal.area', 'goal.course'])
    await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
})
test.afterEach(async ({ request }) => endOpenSession(request))

for (const narrow of [false, true])
  test(`lesson retry survives reload with text and draft (${narrow ? 'narrow' : 'desktop'})`, async ({
    page,
    request,
  }) => {
    if (narrow) await page.setViewportSize({ width: 390, height: 844 })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
    await expectOk(
      await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
    )
    const calls: { key: string | undefined; body: string | null }[] = []
    await page.route('**/api/tutor/stream', async (route) => {
      calls.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData() })
      const token = (text: string) => `event: token\ndata: ${JSON.stringify({ text })}\n\n`
      const body =
        calls.length === 1
          ? token('Keep this partial explanation.')
          : `event: meta\ndata: ${JSON.stringify({ replayed: true, session_id: session.id, turn_id: 'saved', hint_level: 0 })}\n\n` +
            token('Recovered full explanation.') +
            `event: done\ndata: ${JSON.stringify({ turn_id: 'saved', outcome: 'ok', text: 'Recovered full explanation.', sources: [], dropped: [], flagged: [] })}\n\n`
      await route.fulfill({ contentType: 'text/event-stream', body })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /^Continue$/ }).click()
    const input = page.getByLabel('Ask about this lesson (optional)')
    await input.fill('Explain this step')
    await page.getByRole('button', { name: 'Send lesson question' }).click()
    await expect(page.getByText('Keep this partial explanation.', { exact: true })).toBeVisible()
    await input.fill('My next unsent question')
    await page.reload()
    await expect(input).toHaveValue('My next unsent question')
    await expect(page.getByText('Keep this partial explanation.', { exact: true })).toBeVisible()
    expect(calls).toHaveLength(1)
    const retry = page.getByRole('button', { name: 'Retry previous request' })
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Recovered full explanation.', { exact: true })).toBeVisible()
    await expect(page.getByText(/Recovered the original reply/)).toBeVisible()
    await expect(input).toHaveValue('My next unsent question')
    expect(calls).toHaveLength(2)
    expect(calls[0].key).toBeTruthy()
    expect(calls[1]).toEqual(calls[0])
  })
