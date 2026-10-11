import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [390, 1280]) test(`playground accessible regions at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/playground')
  await expect(page.getByRole('region', { name: 'Tutor conversation', exact: true })).toHaveCount(1)
  await expect(page.getByRole('region', { name: 'Learning context and tools', exact: true })).toBeVisible()
  await page.addScriptTag({ content: axe.source })
  const violations = await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run(document, {
    runOnly: { type: 'rule', values: ['aria-prohibited-attr', 'region'] },
  })).violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) })))
  expect(violations).toEqual([])
})
