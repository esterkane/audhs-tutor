import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`preferences page heading and keyboard save at ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let font = 'normal'
    const writes: unknown[] = []
    await page.route('**/api/preferences', async route => {
      if (route.request().method() === 'PUT') {
        const body = route.request().postDataJSON()
        writes.push(body)
        font = body.value
      }
      await route.fulfill({ json: { values: { 'ui.font_scale': font }, specs: [
        { key: 'ui.font_scale', type: 'enum', choices: ['normal', 'large'], default: 'normal', description: 'Text size' },
      ] } })
    })
    await page.goto('/')
    await page.getByText('More tools', { exact: true }).click()
    await page.getByRole('link', { name: 'Preferences', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeVisible()
    await page.screenshot({ path: info.outputPath('preferences.png'), fullPage: true })
    await expect(page.getByRole('heading', { name: 'Preferences', level: 1, exact: true })).toBeVisible({ timeout: 2000 })
    expect(await page.locator('main h1').count()).toBe(1)
    await page.getByRole('button', { name: 'large', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-font', 'large')
    expect(writes).toEqual([{ key: 'ui.font_scale', value: 'large' }])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('button', { name: 'Back', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/$/)
  })
}


test('preferences retains page orientation while loading', async ({ page }) => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/preferences', async route => {
    await pending
    await route.fulfill({ json: { values: {}, specs: [] } })
  })
  try {
    await page.goto('/preferences')
    await expect(page.getByText('Loading preferences…', { exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Preferences', level: 1, exact: true })).toBeVisible()
    release()
    await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeVisible()
    expect(await page.locator('main h1').count()).toBe(1)
    await expect(page.getByRole('heading', { name: 'Adaptation log', level: 2 })).toBeVisible()
  } finally { release() }
})
