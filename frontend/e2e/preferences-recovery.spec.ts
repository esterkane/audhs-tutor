import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`preferences read failure and stale cache recovery ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let failing = true
    let font = 'normal'
    const writes: unknown[] = []
    const preferences = () => ({ values: { 'ui.font_scale': font }, specs: [
      { key: 'ui.font_scale', type: 'enum', choices: ['normal', 'large'], default: 'normal', description: 'Text size' },
    ] })
    await page.route('**/api/preferences', async route => {
      if (route.request().method() === 'PUT') {
        const body = route.request().postDataJSON()
        writes.push(body)
        font = body.value
        await route.fulfill({ json: preferences() })
      } else if (failing) await route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
      else await route.fulfill({ json: preferences() })
    })
    await page.goto('/preferences')
    await expect(page.getByText('Could not load preferences.', { exact: true })).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: info.outputPath('failed-read.png'), fullPage: true })
    await expect(page.getByRole('heading', { level: 1, name: 'Preferences' })).toBeVisible()
    failing = false
    const retry = page.getByRole('button', { name: 'Retry loading preferences', exact: true })
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'normal', exact: true })).toHaveAttribute('aria-pressed', 'true')
    expect(writes).toEqual([])
    await page.getByRole('link', { name: 'Home', exact: true }).click()
    failing = true
    await page.getByText('More tools', { exact: true }).click()
    await page.getByRole('link', { name: 'Preferences', exact: true }).click()
    await expect(page.getByText('Could not refresh preferences. Showing the last loaded settings.', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'normal', exact: true })).toHaveAttribute('aria-pressed', 'true')
    await page.screenshot({ path: info.outputPath('cached-read.png'), fullPage: true })
    await page.getByRole('button', { name: 'large', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-font', 'large')
    expect(writes).toEqual([{ key: 'ui.font_scale', value: 'large' }])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
