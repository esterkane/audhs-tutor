import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { API, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(`comfort settings persist and focus remains escapable at ${width}`, async ({ page, request }, info) => {
    const old = (await (await request.get(`${API}/api/preferences`)).json()).values
    const keys = ['ui.motion', 'ui.font_scale', 'ui.readable_font', 'ui.break_reminder']
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences')
      await page.getByRole('button', { name: 'Extra large', exact: true }).click()
      await expect(page.locator('html')).toHaveAttribute('data-text-size', 'xl')
      await page.getByRole('button', { name: 'full', exact: true }).click()
      await expect(page.locator('html')).toHaveAttribute('data-motion', 'off') // OS reduce ceiling
      await page.emulateMedia({ reducedMotion: 'no-preference' })
      await expect(page.locator('html')).toHaveAttribute('data-motion', 'full')
      await page.getByRole('switch', { name: "Use the device's familiar system font" }).click()
      await expect(page.locator('html')).toHaveAttribute('data-font', 'readable')
      await page.reload()
      await expect(page.locator('html')).toHaveAttribute('data-text-size', 'xl')
      await expect(page.locator('html')).toHaveAttribute('data-effects', 'off')
      await page.getByRole('button', { name: 'Focus mode', exact: true }).click()
      await expect(page.locator('html')).toHaveAttribute('data-focus', 'on')
      const exit = page.getByRole('button', { name: 'Exit focus mode', exact: true })
      await expect(exit).toBeVisible()
      await exit.focus()
      expect(await exit.evaluate(el => getComputedStyle(el).outlineWidth)).toBe('3px')
      await page.reload()
      await expect(exit).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(page.getByRole('button', { name: 'Focus mode', exact: true })).toBeVisible()
      await expect(page.locator('html')).toHaveAttribute('data-focus', 'off')
      await page.emulateMedia({ reducedMotion: 'reduce' })
      await expect(page.locator('html')).toHaveAttribute('data-motion', 'off')
      expect(await exit.count()).toBe(0)
      expect(await page.locator('button').first().evaluate(el => getComputedStyle(el).transitionDuration)).toBe('0s')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.addScriptTag({ content: axe.source })
      const violations = await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run(document)).violations.filter(v => v.impact === 'serious' || v.impact === 'critical'))
      expect(violations).toEqual([])
      await page.screenshot({ path: info.outputPath("comfort.png"), fullPage: true })
    } finally {
      for (const key of keys) await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value: old[key] } }))
    }
  })
}
