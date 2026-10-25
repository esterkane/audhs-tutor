import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) for (const theme of ['light', 'dark']) {
  test(`segmented preferences remain readable and operable at ${width} ${theme}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let choice = 'normal'
    await page.route('**/api/preferences', async route => {
      if (route.request().method() === 'PUT') {
        expect(route.request().postDataJSON()).toEqual({ key: 'ui.font_scale', value: 'large' })
        choice = 'large'
      }
      await route.fulfill({ json: { values: { 'ui.font_scale': choice, 'ui.theme': theme }, specs: [
        { key: 'ui.font_scale', type: 'enum', description: 'Text size', choices: ['normal', 'large'] },
        { key: 'tutor.representation_default', type: 'enum', description: 'Explanation format', choices: ['', 'worked_example', 'diagram', 'code'] },
      ] } })
    })
    await page.goto('/preferences')
    const group = page.getByRole('group', { name: 'Text size', exact: true })
    await expect(group.getByRole('button', { name: 'Standard', exact: true })).toHaveAttribute('aria-pressed', 'true')
    const large = group.getByRole('button', { name: 'Large', exact: true })
    await large.focus()
    await page.keyboard.press('Space')
    await expect(large).toHaveAttribute('aria-pressed', 'true')
    await expect(group.getByRole('button', { name: 'Standard', exact: true })).toHaveAttribute('aria-pressed', 'false')
    expect((await large.boundingBox())!.height).toBeGreaterThanOrEqual(44)
    await expect(large).toBeFocused()
    await large.scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('segmented.png') })
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await expect(page.getByRole('button', { name: 'No preferred format', exact: true })).toBeVisible()
    await page.keyboard.press('Tab')
    await expect(large).not.toBeFocused()
  })
}
