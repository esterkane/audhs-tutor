import { expect, test } from '@playwright/test'
for (const width of [390, 1280]) {
  test(`canvas precedes optional guidance ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/playground/visualizer')
    const preview = page.getByLabel('Audio-reactive visual preview')
    await expect(preview).toBeVisible()
    expect((await preview.boundingBox())!.y).toBeLessThan(500)
    const summary = page.locator('summary').filter({ hasText: 'How it works and what is saved' })
    const disclosure = summary.locator('..')
    await expect(disclosure).not.toHaveAttribute('open', '')
    await page.screenshot({ path: info.outputPath('canvas-first.png') })
    await summary.focus()
    await page.keyboard.press('Enter')
    await expect(disclosure).toHaveAttribute('open', '')
    await expect(disclosure).toContainText('Files and positions stay only in this tab until reload')
    await expect(disclosure).toContainText('Save a preset to add it to your collection')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
