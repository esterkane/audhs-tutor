import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test.afterEach(async ({ request }) => {
  await endOpenSession(request)
  await request.put(`${API}/api/preferences`, { data: { key: 'voice.enabled', value: false } })
})

test('reading and voice coordinate without losing received text', async ({ page, request }) => {
  await endOpenSession(request)
  for (const key of ['goal.area', 'goal.course'])
    await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
  await request.put(`${API}/api/preferences`, { data: { key: 'voice.enabled', value: true } })
  const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
  await expectOk(response)
  const session = await response.json()
  const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
  await expectOk(
    await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
  )
  await page.addInitScript(() => {
    // No physical output or microphone. Synthesis is deliberately held below.
    class SilentContext {
      state = 'running'
      resume() {
        return Promise.resolve()
      }
      close() {
        this.state = 'closed'
        return Promise.resolve()
      }
    }
    Object.defineProperty(window, 'AudioContext', { value: SilentContext })
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      value: () => {
        throw new Error('No microphone allowed in this journey')
      },
    })
  })
  await page.route('**/api/voice/speak', () => {
    /* pending until owner aborts */
  })
  let stopped = 0
  await page.routeWebSocket('**/api/voice/ws', (ws) => {
    ws.onMessage((data) => {
      const message = JSON.parse(String(data))
      if (message.type === 'start') ws.send(JSON.stringify({ type: 'ready', text_only: false }))
      if (message.type === 'text') {
        ws.send(JSON.stringify({ type: 'token', text: 'Keep this received explanation.' }))
      }
      if (message.type === 'stop') stopped++
    })
  })
  await page.goto('/')
  await page.getByRole('button', { name: /^Resume previous session/ }).click()
  const listen = page.getByRole('button', { name: 'Listen to explanation', exact: true }).first()
  await listen.click()
  await page.getByRole('button', { name: 'Talk instead' }).click()
  await page.getByRole('button', { name: 'Connect', exact: true }).click()
  await expect(page.getByText('Preparing audio…', { exact: true })).toBeVisible()
  await page.getByLabel('Type instead').fill('Explain this step')
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  await expect(page.getByText('Audio stopped because voice activity started.')).toBeVisible()
  await expect(page.getByText('Keep this received explanation.', { exact: true })).toBeVisible()
  const controls = page.locator('header details').filter({ hasText: 'Audio controls' })
  await controls.locator('summary').click()
  await expect(controls.getByRole('button', { name: 'Stop voice activity' })).toBeVisible()
  await expect(controls.getByRole('button', { name: 'Pause reading' })).toHaveCount(0)
  await listen.click()
  await expect(
    page.getByText('Voice activity stopped because another reading started. Received text is kept.'),
  ).toBeVisible()
  await expect(page.getByText('Keep this received explanation.', { exact: true })).toBeVisible()
  await expect.poll(() => stopped).toBe(1)
  await controls.getByRole('button', { name: 'Stop reading', exact: true }).click()
  await expect(page.getByText('Audio stopped. Listen again starts from the beginning.')).toBeVisible()
})
