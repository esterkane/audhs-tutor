import { expect, test } from '@playwright/test'
import { API, openMainMenu } from './helpers'

for (const width of [390, 1280]) {
  test(`returning during a save preserves the confirmed preference at ${width}`, async ({ page, request }, info) => {
    expect((await request.put(`${API}/api/preferences`, { data: { key: 'ui.font_scale', value: 'normal' } })).ok()).toBe(true)
    let releaseSave!: () => void
    let releaseRead!: () => void
    const saveGate = new Promise<void>(resolve => { releaseSave = resolve })
    const readGate = new Promise<void>(resolve => { releaseRead = resolve })
    let saving = false
    let staleRead = false
    let writes = 0
    await page.route('**/api/preferences', async route => {
      if (route.request().method() === 'PUT') {
        writes++
        saving = true
        await saveGate
        const response = await route.fetch()
        await route.fulfill({ response })
      } else if (saving) {
        const response = await route.fetch()
        staleRead = true
        await readGate
        await route.fulfill({ response }).catch(() => {}) // Correct recovery cancels this read.
      } else await route.continue()
    })
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences')
      await expect(page.getByRole('button', { name: 'normal', exact: true })).toHaveAttribute('aria-pressed', 'true')
      const large = page.getByRole('button', { name: 'large', exact: true })
      await large.focus()
      await page.keyboard.press('Enter')
      await expect.poll(() => saving).toBe(true)
      await openMainMenu(page)
      await page.getByRole('link', { name: 'Home', exact: true }).click()
      await openMainMenu(page)
      await page.getByText('Manage', { exact: true }).click()
      await page.getByRole('link', { name: 'Preferences', exact: true }).click()
      await expect.poll(() => staleRead).toBe(true)
      releaseSave()
      await expect(large).toHaveAttribute('aria-pressed', 'true')
      releaseRead()
      await page.waitForTimeout(150)
      await expect(page.locator('html')).toHaveAttribute('data-font', 'large')
      await expect(large).toHaveAttribute('aria-pressed', 'true')
      expect(writes).toBe(1)
      await large.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath('saved-after-return.png') })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    } finally { releaseSave(); releaseRead() }
  })
}
