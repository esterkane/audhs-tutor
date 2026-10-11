import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`direct preferences entry returns safely inside app ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preferences')
    const back = page.getByRole('button', { name: 'Back', exact: true })
    await back.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('main')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  })
}
