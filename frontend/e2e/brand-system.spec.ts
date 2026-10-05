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

test('brand and quick navigation reflow at 320px with enlarged text', async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/search')
  // Text enlargement is distinct from browser zoom; retain both as separate gates.
  await page.evaluate(async () => {
    document.documentElement.style.fontSize = '200%'
    await document.fonts.ready
  })
  const trigger = page.locator('header').getByRole('button', { name: 'Search or go to' })
  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Search or go to' })
  await expect(dialog).toBeVisible()
  const input = dialog.getByRole('searchbox')
  await input.fill('skill')
  await expect(dialog.getByRole('link', { name: 'Skill map', exact: true })).toBeVisible()
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
  const closeBox = await dialog.getByRole('button', { name: 'Close', exact: true }).boundingBox()
  const dialogBox = await dialog.boundingBox()
  expect(closeBox!.y).toBeGreaterThanOrEqual(dialogBox!.y)
  expect(closeBox!.y + closeBox!.height).toBeLessThanOrEqual(dialogBox!.y + dialogBox!.height)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('large-text.png'), fullPage: true })
  await input.press('Escape')
  await expect(trigger).toBeFocused()
})

test('font failure retains readable system fallback', async ({ page }, info) => {
  await page.route('**/fonts/**', route => route.abort())
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/search')
  await page.evaluate(() => document.fonts.ready)
  await expect(page.getByRole('heading', { name: 'Search material', exact: true })).toBeVisible()
  const field = page.getByRole('searchbox', { name: 'Search phrase', exact: true })
  await field.fill('still usable')
  await expect(field).toHaveValue('still usable')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('font-fallback.png'), fullPage: true })
})
