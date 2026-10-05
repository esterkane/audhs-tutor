import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`rapid preference changes preserve the last intent at ${width}`, async ({ page }, info) => {
    let release!: () => void
    const blocked = new Promise<void>(resolve => { release = resolve })
    let committed!: () => void
    const firstCommitted = new Promise<void>(resolve => { committed = resolve })
    const writes: unknown[] = []
    await page.route('**/api/preferences', async route => {
      if (route.request().method() !== 'PUT') return route.continue()
      writes.push(route.request().postDataJSON())
      const response = await route.fetch()
      if (writes.length === 1) { committed(); await blocked }
      await route.fulfill({ response })
    })
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences')
      await page.getByRole('button', { name: 'large', exact: true }).click()
      await firstCommitted
      const normal = page.getByRole('button', { name: 'normal', exact: true })
      await normal.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('status').filter({ hasText: 'Saving preferences…' })).toBeVisible()
      // Give the route observer time to catch an incorrectly concurrent second request.
      await page.waitForTimeout(150)
      expect(writes).toEqual([{ key: 'ui.font_scale', value: 'large' }])
      const lastSave = page.waitForResponse(response => response.url().endsWith('/api/preferences') && response.request().method() === 'PUT' && response.request().postDataJSON().value === 'normal')
      release()
      expect((await lastSave).ok()).toBe(true)
      await expect(page.locator('html')).toHaveAttribute('data-font', 'normal')
      await expect(page.getByText('Saving preferences…', { exact: true })).toHaveCount(0)
      expect(writes).toEqual([{ key: 'ui.font_scale', value: 'large' }, { key: 'ui.font_scale', value: 'normal' }])
      await page.reload()
      await expect(normal).toHaveAttribute('aria-pressed', 'true')
      await expect(page.locator('html')).toHaveAttribute('data-font', 'normal')
      await normal.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath('last-preference-preserved.png') })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    } finally { release() }
  })
}
