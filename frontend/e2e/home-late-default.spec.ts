import { expect, test } from '@playwright/test'
import { API, endOpenSession } from './helpers'

// Preferences live in the shared sandbox, not in Playwright's fresh browser context.
let previousMode: string
test.beforeEach(async ({ request }) => {
  const response = await request.get(`${API}/api/preferences`)
  expect(response.ok()).toBe(true)
  previousMode = (await response.json()).values['session.default_mode']
})
test.afterEach(async ({ request }) => {
  expect((await request.put(`${API}/api/preferences`, {
    data: { key: 'session.default_mode', value: previousMode },
  })).ok()).toBe(true)
})

for (const width of [390, 1280]) {
  test(`an explicit Home mode wins over delayed preferences at ${width}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    expect((await request.put(`${API}/api/preferences`, { data: { key: 'session.default_mode', value: 'low_capacity' } })).ok()).toBe(true)
    let release!: () => void
    const gate = new Promise<void>(resolve => { release = resolve })
    await page.route('**/api/preferences', async route => {
      if (route.request().method() !== 'GET') return route.continue()
      const response = await route.fetch()
      await gate
      await route.fulfill({ response })
    })
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByText('Session options', { exact: true }).click()
      const novelty = page.getByRole('button', { name: /Novelty Fresh material/ })
      await novelty.focus()
      await page.keyboard.press('Enter')
      await expect(novelty).toHaveAttribute('aria-pressed', 'true')
      const received = page.waitForResponse(response => response.url().endsWith('/api/preferences'))
      release()
      await received
      await page.waitForTimeout(150)
      await expect(novelty).toHaveAttribute('aria-pressed', 'true')
      await expect(page.getByText(/Novelty · energy 3 · Direct explanations/)).toBeVisible()
      expect(await (await request.get(`${API}/api/sessions/current`)).json()).toBeNull()
      expect((await (await request.get(`${API}/api/preferences`)).json()).values['session.default_mode']).toBe('low_capacity')
      await novelty.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath('chosen-mode-preserved.png') })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    } finally { release() }
  })
}

test('saved mode still preselects Home before an explicit choice', async ({ page, request }) => {
  await endOpenSession(request)
  expect((await request.put(`${API}/api/preferences`, { data: { key: 'session.default_mode', value: 'low_capacity' } })).ok()).toBe(true)
  await page.goto('/')
  await expect(page.getByText(/Low capacity · energy 3 · Direct explanations/)).toBeVisible()
  await page.getByText('Session options', { exact: true }).click()
  await expect(page.getByRole('button', { name: /Low capacity Shortest useful path/ })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('Preselected from your default (Preferences). Change it freely.', { exact: true })).toBeVisible()
})
