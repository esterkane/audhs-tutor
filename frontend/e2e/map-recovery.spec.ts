import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`map read recovery preserves nodes ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let failing = true
    await page.route('**/api/skills/map', route => failing
      ? route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
      : route.fulfill({ json: {
        nodes: [
          { id: 'fixture-one', title: 'First concept', mastery: 0.4, unlocked: true, is_next: true, memory: { items: 3, due: 1 } },
          { id: 'fixture-two', title: 'Later concept', mastery: 0, unlocked: false, is_next: false, memory: { items: 0, due: 0 } },
        ], edges: [], mermaid: 'graph LR\n a[First concept] --> b[Later concept]',
      } }))
    await page.goto('/map')
    await expect(page.getByText('Could not load the skill map.', { exact: true })).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: info.outputPath('failed-read.png'), fullPage: true })
    failing = false
    await page.getByRole('button', { name: 'Retry loading map', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('listitem').filter({ hasText: 'First concept' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Locked', exact: true })).toBeDisabled()
    failing = true
    if (width < 768) {
      await page.getByRole('button', { name: 'Menu · Skill map', exact: true }).focus()
      await page.keyboard.press('Enter')
    }
    await page.getByRole('link', { name: 'Home', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Your next step', exact: true })).toBeVisible()
    await page.goBack()
    await expect(page.getByText('Could not refresh the skill map. Showing the last loaded map.', { exact: true })).toBeVisible()
    await expect(page.getByRole('listitem').filter({ hasText: 'First concept' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Skill map', level: 1 })).toBeVisible()
    await expect(page.locator('main svg')).toBeVisible()
    await page.screenshot({ path: info.outputPath('cached-read.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('button', { name: 'Learn this', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\?lesson=fixture-one$/)
  })
}
