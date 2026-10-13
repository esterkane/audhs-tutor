import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const first of ['Save and finish session', 'End session']) test(`recap finish locks competing controls: ${first}`, async ({ page, request }) => {
  await endOpenSession(request)
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  try {
    await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
    await page.setViewportSize({ width: first.startsWith('Save') ? 390 : 1280, height: 900 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await page.goto('/recap')
    await page.getByLabel('One line for next time (optional)').fill('Keep this recap')
    let calls = 0
    await page.route('**/api/sessions/*/end', async route => {
      calls++
      await held
      await route.continue()
    })
    await page.getByRole('button', { name: first, exact: true }).click()
    await expect.poll(() => calls).toBe(1)
    await expect(page.getByRole('button', { name: 'Change topic', exact: true })).toBeDisabled()
    await expect(page.getByLabel('One line for next time (optional)')).toBeDisabled()
    if (first.startsWith('Save')) await expect(page.getByRole('button', { name: 'End session', exact: true })).toBeDisabled()
    else await expect(page.getByRole('button', { name: /Save and finish session|Saving…|Ending session…/ })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Return Home', exact: true })).toBeEnabled()
    await expect(page.getByRole('status').filter({ hasText: 'Returning Home does not cancel it' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: `/tmp/recap-pending-${first.startsWith('Save') ? 390 : 1280}.png`, fullPage: true })
    release()
    if (first.startsWith('Save')) await expect(page.getByRole('heading', { name: 'Session saved' })).toBeVisible()
    else await expect(page).toHaveURL(/\/$/)
    expect(calls).toBe(1)
  } finally { release(); await endOpenSession(request) }
})
