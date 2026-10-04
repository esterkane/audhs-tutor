import { readFile, writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import axe from 'axe-core'

// Run only with the standalone design config, outside production browser journeys.
test.skip(!process.env.AUDHS_DESIGN_REVIEW, 'Use AUDHS_DESIGN_REVIEW=1 and design.playwright.config.ts')
for (const direction of ['quiet', 'structured', 'canvas']) {
  for (const width of [320, 390, 1280]) {
    test(`${direction} at ${width}px`, async ({ page }, info) => {
      const html = await readFile(new URL('../../design-experiments/ux-directions/index.html', import.meta.url), 'utf8')
      const requests: string[] = []
      await page.route('**/*', route => {
        requests.push(route.request().url())
        return route.fulfill({ contentType: 'text/html', body: html })
      })
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`http://prototype.test/?direction=${direction}`)
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Comparing groups fairly')
      await page.addScriptTag({ content: axe.source })
      const violations = await page.evaluate(async () =>
        (await (window as unknown as { axe: typeof axe }).axe.run(document, {
          runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
        })).violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target) })),
      )
      await writeFile(info.outputPath('accessibility.json'), JSON.stringify(violations, null, 2))
      expect(violations).toEqual([])
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('initial.png'), fullPage: true })
      await page.getByRole('button', { name: 'Try a comparison' }).focus()
      await page.keyboard.press('Enter')
      const note = page.getByLabel('What would you compare next, and why?')
      await expect(note).toBeFocused()
      await note.fill('Compare the same proportions.')
      await page.getByRole('button', { name: "I don't understand yet" }).click()
      await expect(page.getByText(/Imagine each group started with 10/)).toBeVisible()
      await expect(page.getByRole('heading', { name: 'A smaller step' })).toBeFocused()
      await page.getByRole('button', { name: 'More detail', exact: true }).click()
      await expect(page.getByText(/Retention = remaining/)).toBeVisible()
      await page.getByRole('button', { name: 'Save as clear' }).click()
      await page.getByRole('button', { name: 'Undo label' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Save as clear' })).toHaveAttribute('aria-pressed', 'false')
      await page.getByRole('button', { name: 'Pause and return Home' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Resume this lesson' })).toBeFocused()
      await page.keyboard.press('Enter')
      await expect(note).toHaveValue('Compare the same proportions.')
      await page.getByLabel('Compare layout').selectOption(direction === 'quiet' ? 'canvas' : 'quiet')
      await expect(note).toHaveValue('Compare the same proportions.')
      await page.getByRole('button', { name: 'Library', exact: true }).click()
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Library')
      await expect(page.getByRole('button', { name: 'Library', exact: true })).toHaveAttribute('aria-current', 'page')
      await page.getByRole('button', { name: 'Return to this lesson' }).click()
      await expect(note).toHaveValue('Compare the same proportions.')
      expect(requests).toHaveLength(1)
    })
  }
}
