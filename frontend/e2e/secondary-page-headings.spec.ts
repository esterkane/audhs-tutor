import { expect, test } from '@playwright/test'

const pages = [
  ['/areas', 'Learning areas'], ['/programs', 'Project study'],
  ['/curriculum', 'Knowledge material'], ['/corpus', 'Corpus'],
  ['/models', 'Models'], ['/experiments', 'Experiments (n-of-1)'],
  ['/vocab', 'Vocabulary decks'], ['/together', 'Working alongside'],
  ['/playground', 'Coding playground'], ['/playground/visualizer', 'Audio visualizer lab'],
  ['/missing-page', 'Page not found'], ['/corrections', 'Question correction drafts'],
]
for (const width of [320, 1280]) test(`secondary pages identify themselves at ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  for (const [path, title] of pages) {
    await page.goto(path)
    const heading = page.getByRole('heading', { level: 1, name: title, exact: true })
    await expect(heading).toBeVisible()
    await expect(page.locator('main h1')).toHaveCount(1)
    expect(await heading.evaluate(el => getComputedStyle(el).fontSize)).toBe('22px')
    const bounds = await heading.boundingBox()
    expect(bounds!.x + bounds!.width, path).toBeLessThanOrEqual(width + 1)
    await page.keyboard.press('Tab')
    expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true)
    if (path === '/areas' || path === '/programs') await page.screenshot({ path: info.outputPath(`${path.slice(1)}.png`) })
  }
})
