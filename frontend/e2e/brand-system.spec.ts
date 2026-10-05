import { expect, test } from '@playwright/test'

for (const theme of ['light', 'dark'] as const) for (const width of [390, 1280]) test(`local brand and typography ${theme} ${width}`, async ({ page }, info) => {
  const external: string[] = []
  page.on('request', request => {
    if (['font', 'image'].includes(request.resourceType()) && !new URL(request.url()).hostname.match(/^(localhost|127\.0\.0\.1)$/)) external.push(request.url())
  })
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/search')
  await page.evaluate(async theme => {
    document.documentElement.dataset.theme = theme
    await document.fonts.load('400 16px Inter')
    await document.fonts.load('400 16px "Roboto Mono"')
    await document.fonts.ready
  }, theme)
  const brand = page.locator('header').getByRole('link', { name: 'AuDHS Tutor', exact: true })
  await expect(brand).toBeVisible()
  expect(await page.evaluate(() => document.fonts.check('400 16px Inter') && document.fonts.check('400 16px "Roboto Mono"'))).toBe(true)
  expect(await page.evaluate(() => getComputedStyle(document.body).fontFamily)).toContain('Inter')
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(theme === 'light' ? 'rgb(247, 248, 252)' : 'rgb(29, 30, 36)')
  expect(external).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('brand.png'), fullPage: true })
  await brand.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/$/)
})
