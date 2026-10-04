import { openMainMenu } from './helpers'
import { expect, test } from '@playwright/test'

for (const width of [320, 390, 1280]) {
  test(`parking capture stays out of navigation ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: unknown[] = []
    await page.route('**/api/parking', async route => {
      if (route.request().method() === 'POST') {
        writes.push(route.request().postDataJSON())
        await route.fulfill({ status: 201, json: { id: 'fixture', text: 'Keep this thought', status: 'parked' } })
      } else await route.fulfill({ json: [] })
    })
    await page.goto('/curriculum')
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    await openMainMenu(page)
    await page.getByText('Manage · Lesson drafts', { exact: true }).click()
    const park = page.getByRole('button', { name: 'Parking lot: park a tangent for later' })
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    const triggerBox = await park.boundingBox()
    const navBox = await nav.boundingBox()
    expect(triggerBox!.y + triggerBox!.height).toBeLessThanOrEqual(navBox!.y)
    await park.focus()
    await page.keyboard.press('Enter')
    const input = page.getByRole('textbox', { name: 'Tangent to park' })
    await expect(input).toBeFocused()
    await input.fill('Keep this thought')
    await page.keyboard.press('Escape')
    await expect(park).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(input).toHaveValue('Keep this thought')
    const dialog = page.getByRole('dialog')
    const box = await dialog.boundingBox()
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.y + box!.height).toBeLessThanOrEqual(900)
    await page.keyboard.press('Enter')
    await expect(dialog).toHaveCount(0)
    await expect(park).toBeFocused()
    await expect(page.getByRole('status').filter({ hasText: 'Parked.' })).toBeVisible()
    expect(writes).toHaveLength(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.screenshot({ path: info.outputPath('parked-header.png'), fullPage: true })
  })
}
