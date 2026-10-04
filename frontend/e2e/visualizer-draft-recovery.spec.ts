import { expect, test } from '@playwright/test'
for (const width of [390, 1280]) {
  test(`visualizer draft and undo survive route exit and reload ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/playground/visualizer')
    await page.getByRole('button', { name: 'Create', exact: true }).click()
    await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
    const editor = page.getByRole('textbox', { name: 'Preset JSON', exact: true })
    const original = await editor.inputValue()
    await editor.fill('{unfinished')
    await page.getByRole('link', { name: 'Coding playground', exact: false }).click()
    await page.getByRole('link', { name: 'Open audio visualizer lab' }).click()
    await expect(page.getByRole('button', { name: 'Create', exact: true })).toHaveAttribute('aria-pressed', 'true')
    await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
    await expect(editor).toHaveValue('{unfinished')
    await page.reload()
    await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
    await expect(editor).toHaveValue('{unfinished')
    const undo = page.getByRole('button', { name: 'Undo draft', exact: true })
    await undo.focus()
    await page.keyboard.press('Enter')
    await expect(editor).toHaveValue(original)
    await expect(page.getByRole('button', { name: 'Start demo', exact: true })).toBeEnabled()
    await page.screenshot({ path: info.outputPath('recovered.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('denied recovery storage keeps the tab draft and offers export', async ({ page }) => {
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = function (key, value) {
      if (key === 'audhs:visualizer:workspace:v1') throw new DOMException('quota', 'QuotaExceededError')
      return original.call(this, key, value)
    }
  })
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  await page.getByRole('textbox', { name: 'Preset JSON', exact: true }).fill('{keep-this')
  await expect(page.getByRole('status').filter({ hasText: 'Browser recovery is unavailable' })).toBeVisible()
  await page.getByRole('link', { name: 'Coding playground', exact: false }).click()
  await page.getByRole('link', { name: 'Open audio visualizer lab' }).click()
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Preset JSON', exact: true })).toHaveValue('{keep-this')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export editing draft', exact: true }).click()
  expect((await download).suggestedFilename()).toBe('visualizer-draft.txt')
})
