import { expect, test } from '@playwright/test'

for (const width of [390, 800, 1280]) {
  test(`Home puts the saved topic first at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) =>
      route.fulfill({
        json: {
          id: 'fixture',
          active_skill: { id: 'topic', title: 'Comparing groups' },
          state: { skill_id: 'topic', block_status: 'running', phase: 'review', plan_complete: false },
        },
      }),
    )
    await page.goto('/')
    const resume = page.getByRole('button', { name: /^Resume previous session: Comparing groups/ })
    await expect(resume).toBeVisible()
    await expect(page.getByText('Next: continue your saved review.')).toBeVisible()
    const options = page.getByText('Session options', { exact: true })
    await expect(options.locator('..')).not.toHaveAttribute('open')
    const box = await resume.boundingBox()
    expect(box!.y).toBeLessThan((await options.boundingBox())!.y)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await resume.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/review$/)
  })
}
