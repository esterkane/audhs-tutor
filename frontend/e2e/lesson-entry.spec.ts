import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test('general explanation preserves a restored question without sending it', async ({ page, request }) => {
  await endOpenSession(request)
  try {
    for (const key of ['goal.area', 'goal.course'])
      await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: {
      session_id: session.id, index: session.plan.findIndex((block: { type: string }) => block.type === 'new_material'),
    } }))
    const sent: string[] = []
    await page.route('**/api/tutor/stream', route => {
      sent.push(route.request().postDataJSON().text)
      return route.fulfill({ contentType: 'text/event-stream', body:
        `event: token\ndata: {"text":"A useful explanation."}\n\nevent: done\ndata: {"turn_id":"entry","outcome":"ok","text":"A useful explanation.","sources":[],"dropped":[],"flagged":[]}\n\n` })
    })
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    const input = page.getByLabel('Ask about this lesson (optional)')
    const start = page.getByRole('button', { name: 'Start explanation', exact: true })
    await input.fill('My specific saved question')
    await page.reload()
    await expect(input).toHaveValue('My specific saved question')
    await expect(page.getByText('Starting an explanation keeps your draft below without sending it.', { exact: false })).toBeVisible()
    expect(sent).toEqual([])
    await start.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('A useful explanation.', { exact: true })).toBeVisible()
    expect(sent).toHaveLength(1)
    expect(sent[0]).toContain('The idea, A worked example, and Try one step')
    expect(sent[0]).not.toContain('My specific saved question')
    await expect(input).toHaveValue('My specific saved question')
    await input.focus()
    await page.keyboard.press('Tab')
    const send = page.getByRole('button', { name: 'Send lesson question', exact: true })
    await expect(send).toBeFocused()
    await page.keyboard.press('Enter')
    await expect.poll(() => sent.length).toBe(2)
    expect(sent[1]).toBe('My specific saved question')
  } finally { await endOpenSession(request) }
})
