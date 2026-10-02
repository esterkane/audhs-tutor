import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test.afterEach(async ({ request }) => {
  await endOpenSession(request)
  await request.put(`${API}/api/preferences`, { data: { key: 'voice.enabled', value: false } })
})
for (const narrow of [false, true])
  test(`voice draft survives reload without connection (${narrow ? 'narrow' : 'desktop'})`, async ({
    page,
    request,
  }) => {
    await endOpenSession(request)
    if (narrow) await page.setViewportSize({ width: 390, height: 844 })
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
    let sockets = 0
    page.on('websocket', (socket) => {
      if (socket.url().includes('/api/voice/ws')) sockets++
    })
    await page.goto('/')
    await page.getByRole('button', { name: /^Resume previous session/ }).click()
    await page.getByRole('button', { name: 'Talk instead' }).click()
    await page.getByLabel('Type instead').fill('Keep my voice question draft')
    await page.reload()
    await page.getByRole('button', { name: 'Talk instead' }).click()
    await expect(page.getByLabel('Type instead')).toHaveValue('Keep my voice question draft')
    await expect(page.getByText(/Restored voice text/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Connect', exact: true })).toBeVisible()
    expect(sockets).toBe(0)
    const pendingId = '12345678-1234-1234-1234-123456789abc'
    await page.evaluate((id) => {
      const textKey = Object.keys(sessionStorage).find((key) => key.startsWith('voice-text:v1:'))!
      sessionStorage.setItem(textKey.replace('voice-text:v1:', 'voice-request:v1:'), id)
    }, pendingId)
    let lookups = 0
    await page.route('**/api/voice/requests/*?*', async (route) => {
      lookups++
      expect(route.request().method()).toBe('GET')
      await route.fulfill({ json: { request_id: pendingId, status: 'partial', transcript: 'Original voice question', text: 'Recovered partial explanation', interrupted: true, turn: null } })
    })
    await page.reload()
    await page.getByRole('button', { name: 'Talk instead' }).click()
    expect(lookups).toBe(0)
    const check = page.getByRole('button', { name: 'Check saved voice result' })
    await check.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Recovered partial explanation', { exact: true })).toBeVisible()
    await expect(page.getByText(/Recovered partial reply/)).toBeVisible()
    await expect(page.getByLabel('Type instead')).toHaveValue('Keep my voice question draft')
    expect(lookups).toBe(1)
    await page.getByRole('button', { name: 'Dismiss recovery and allow a new question' }).click()
    await expect(page.getByText('Recovered partial explanation', { exact: true })).toBeVisible()
    await page.reload()
    await page.getByRole('button', { name: 'Talk instead' }).click()
    await expect(page.getByText('Recovered partial explanation', { exact: true })).toBeVisible()
    expect(sockets).toBe(0)
    const clear = page.getByRole('button', { name: 'Clear and close panel' })
    await clear.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('button', { name: 'Talk instead' }).click()
    await expect(page.getByLabel('Type instead')).toHaveValue('')
    expect(sockets).toBe(0)
  })
