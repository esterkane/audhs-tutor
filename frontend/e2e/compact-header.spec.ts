import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) {
  test(`compact header retains global controls and page context ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'dark' })
    await page.goto('/practice')
    const header = page.locator('header')
    expect((await header.boundingBox())!.height).toBeLessThanOrEqual(49)
    await expect(header.getByText(/Browse area/)).toHaveCount(0)
    await expect(page.getByText(/Browse area/).first()).toBeVisible()
    for (const name of ['Search or go to', 'Save for later']) {
      const control = header.getByRole('button', { name, exact: true })
      const box = await control.boundingBox()
      expect(box!.height).toBeGreaterThanOrEqual(44)
      expect(box!.width).toBeGreaterThanOrEqual(44)
      await control.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('dialog')).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(control).toBeFocused()
    }
    await page.screenshot({ path: info.outputPath('compact-header.png'), fullPage: true })
    const audio = header.locator('summary')
    await audio.focus()
    await page.keyboard.press('Enter')
    await expect(header.getByLabel('Audio volume')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: info.outputPath('audio-expanded.png'), fullPage: true })
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    await page.emulateMedia({ colorScheme: 'light' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(header.getByRole('button', { name: 'Save for later' })).toBeVisible()
    await page.screenshot({ path: info.outputPath('large-text.png'), fullPage: true })
  })
}
