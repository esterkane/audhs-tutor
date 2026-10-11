import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Practice offers explicit activities without changing the session ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  const writes: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/') && !['GET', 'HEAD'].includes(request.method())) writes.push(request.url())
  })
  await page.goto('/practice')
  await expect(page.getByRole('heading', { name: 'Practice', exact: true })).toBeVisible()
  const activities = [
    ['Open learning session', '/learn'], ['Open playground', '/playground'],
    ['Open language activities', '/vocab'], ['Open project study', '/programs'],
  ]
  const first = page.getByRole('link', { name: activities[0][0], exact: true })
  await first.focus()
  for (const [index, [name, path]] of activities.entries()) {
    const link = page.getByRole('link', { name, exact: true })
    await expect(link).toHaveAttribute('href', path)
    await expect(link).toBeFocused()
    expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44)
    if (index < activities.length - 1) await page.keyboard.press('Tab')
  }
  expect(writes).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('practice.png'), fullPage: true })
  await page.getByRole('link', { name: 'Open language activities' }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/vocab$/)
  await expect(page.getByRole('main')).toBeFocused()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Practice', exact: true })).toBeVisible()
})
