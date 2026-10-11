import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) test(`model controls stay within the page at ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/models')
  await expect(page.getByRole('heading', { level: 1, name: 'Models', exact: true })).toBeVisible()
  await expect(page.locator('main table').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1)
  const models = page.getByRole('region', { name: 'Available models', exact: true })
  await models.focus()
  await expect(models).toBeFocused()
  if (width === 390) {
    await page.keyboard.press('ArrowRight')
    await expect.poll(() => models.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
  }
  await page.screenshot({ path: info.outputPath('models.png'), fullPage: true })
})
