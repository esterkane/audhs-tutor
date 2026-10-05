import { expect, test } from '@playwright/test'
for (const width of [320, 640, 1280]) {
  test(`real preferences at double text size ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preferences')
    await expect(page.getByRole('heading', { name: 'Adaptation log', exact: true })).toBeVisible()
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    await page.screenshot({ path: info.outputPath('preferences-double-text.png'), fullPage: true })
    const overflow = await page.evaluate(() => [...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1).map(el => ({ tag: el.tagName, text: el.textContent?.slice(0, 90), right: el.getBoundingClientRect().right })))
    expect(overflow).toEqual([])
    const code = page.getByRole('button', { name: 'code', exact: true })
    await code.focus()
    const saved = page.waitForResponse(response => response.url().endsWith('/api/preferences') && response.request().method() === 'PUT')
    await page.keyboard.press('Enter')
    expect((await saved).ok()).toBe(true)
    await expect(code).toHaveAttribute('aria-pressed', 'true')
    await code.locator('xpath=ancestor::fieldset').screenshot({ path: info.outputPath('representation-options.png') })
    await page.getByRole('button', { name: 'Back', exact: true }).focus()
    await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeFocused()
  })
}
