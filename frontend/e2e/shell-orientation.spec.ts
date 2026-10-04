import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [1280, 390, 320]) {
  test(`shell orientation, keyboard skip and tools at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/local-learning/program.json', (route) =>
      route.fulfill({ json: { title: 'Fixture', courses: [] } }),
    )
    await page.goto('/programs')
    await expect(page).toHaveTitle('Project study · AuDHS Tutor')
    await expect(page.getByRole('link', { name: 'Projects', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    )
    const navBox = await page.getByRole('navigation', { name: 'Main navigation' }).boundingBox()
    const mainBox = await page.getByRole('main').boundingBox()
    if (width >= 1024) expect(navBox!.x + navBox!.width).toBeLessThanOrEqual(mainBox!.x + 1)
    else expect(navBox!.y + navBox!.height).toBeLessThanOrEqual(mainBox!.y + 1)
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: 'Skip to learning content' })).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('main')).toBeFocused()
    await page.getByText('Explore', { exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('link', { name: 'Learning areas', exact: true }).click()
    await expect(page).toHaveTitle('Learning areas · AuDHS Tutor')
    await expect(page.getByRole('main')).toBeFocused()
    await page.getByText('Manage', { exact: true }).click()
    await page.getByRole('link', { name: 'Lesson drafts', exact: true }).click()
    await expect(page).toHaveTitle('Lesson drafts · AuDHS Tutor')
    await expect(page.getByText('Manage · Lesson drafts', { exact: true })).toBeVisible()
    await page.getByText('Manage · Lesson drafts', { exact: true }).click()
    await expect(page.getByRole('link', { name: 'Lesson drafts', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await page.screenshot({ path: info.outputPath('navigation-normal.png'), fullPage: true })
    await page.goBack()
    await expect(page).toHaveTitle('Learning areas · AuDHS Tutor')
    await expect(page.getByText('Explore · Learning areas', { exact: true })).toBeVisible()
    await page.goForward()
    await expect(page).toHaveTitle('Lesson drafts · AuDHS Tutor')
    await page.getByText('Manage · Lesson drafts', { exact: true }).click()
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '200%'
    })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.addScriptTag({ content: axe.source })
    const violations = await page.evaluate(
      async () =>
        (
          await (window as unknown as { axe: typeof axe }).axe.run('header, nav', {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
          })
        ).violations,
    )
    expect(violations.map((v) => v.id)).toEqual([])
    await page.screenshot({ path: info.outputPath('navigation.png'), fullPage: true })
    await page.goto('/missing-learning-page')
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    await expect(page).toHaveTitle('Page not found · AuDHS Tutor')
    await expect(page.getByRole('link', { name: 'Return Home' })).toHaveAttribute('href', '/')
  })
}
