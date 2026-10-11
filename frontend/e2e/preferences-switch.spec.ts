import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`boolean switch confirms saves and recovers at ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let enabled = false
  let fail = true
  let writes = 0
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  const snapshot = () => ({ values: { 'ui.reduced_motion': enabled }, specs: [{ key: 'ui.reduced_motion', type: 'bool', default: false, description: 'Reduce motion' }] })
  await page.route('**/api/preferences', async route => {
    if (route.request().method() !== 'PUT') return route.fulfill({ json: snapshot() })
    writes++
    if (fail) { await held; return route.fulfill({ status: 503, json: { detail: 'Save unavailable' } }) }
    expect(route.request().postDataJSON()).toEqual({ key: 'ui.reduced_motion', value: true })
    enabled = true
    await route.fulfill({ json: snapshot() })
  })
  await page.goto('/preferences')
  const control = page.getByRole('switch', { name: 'Reduce motion', exact: true })
  await expect(control).not.toBeChecked()
  expect((await page.locator('label').filter({ has: control }).boundingBox())!.height).toBeGreaterThanOrEqual(44)
  await control.focus()
  await page.keyboard.press('Space')
  await expect(control).toBeDisabled()
  await page.keyboard.press('Space')
  expect(writes).toBe(1)
  release()
  await expect(page.getByRole('alert').filter({ hasText: 'Save unavailable' })).toBeVisible()
  await expect(control).not.toBeChecked()
  await expect(control).toBeEnabled()
  fail = false
  await control.focus()
  await page.keyboard.press('Space')
  await expect(control).toBeChecked()
  await expect(control).toBeEnabled()
  await page.reload()
  await expect(control).toBeChecked()
  await control.focus()
  await page.screenshot({ path: info.outputPath('switch-preferences.png') })
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(writes).toBe(2)
})
