import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`vocabulary entry retains work after failed save ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let calls = 0
  await page.route('**/api/vocab*', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    calls++
    return route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Card storage unavailable' } } })
  })
  await page.goto('/vocab')
  const add = page.locator('summary').filter({ hasText: /^Add one card$/ })
  await add.focus()
  await page.keyboard.press('Enter')
  await page.getByLabel('Word', { exact: true }).fill('example')
  await page.getByLabel('Translation', { exact: true }).fill('Beispiel')
  await page.getByRole('button', { name: 'Add card', exact: true }).click()
  await expect(page.getByLabel('Word', { exact: true })).toHaveValue('example')
  await expect(page.getByRole('alert').filter({ hasText: 'Card storage unavailable' })).toBeVisible()
  expect(calls).toBe(1)
  await add.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Word', { exact: true })).toHaveValue('example')
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/vocab', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    calls++
    expect(route.request().postDataJSON().word).toBe(calls === 2 ? 'example' : 'new unsaved word')
    await held
    await route.fulfill({ json: { id: 'fixture-card' } })
  })
  const submit = page.getByRole('button', { name: 'Add card', exact: true })
  await submit.evaluate(button => { (button as HTMLButtonElement).click(); (button as HTMLButtonElement).click() })
  await expect(submit).toBeDisabled()
  await page.getByLabel('Word', { exact: true }).fill('new unsaved word')
  release()
  await expect(page.getByRole('status').filter({ hasText: 'Submitted card saved.' })).toBeVisible()
  await expect(page.getByLabel('Word', { exact: true })).toHaveValue('new unsaved word')
  await expect(page.getByLabel('Translation', { exact: true })).toHaveValue('Beispiel')
  expect(calls).toBe(2)
  for (const label of ['Add one card', 'Import a CSV list']) {
    const summary = page.locator('summary').filter({ hasText: label })
    expect((await summary.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('vocabulary-entry.png'), fullPage: true })
  await submit.click()
  await expect(page.getByLabel('Word', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('Translation', { exact: true })).toHaveValue('')
  expect(calls).toBe(3)
})
