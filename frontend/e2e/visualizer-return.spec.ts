import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`visualizer detour retains coding workspace ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() => localStorage.setItem('code-editor:plain', '1'))
    const writes: string[] = []
    page.on('request', request => {
      if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url())
    })
    await page.goto('/playground?workspace=complete')
    await page.getByRole('textbox', { name: /Python code/ }).fill('print("my experiment")')
    await page.getByRole('link', { name: 'Open audio visualizer lab' }).click()
    await expect(page.getByRole('heading', { name: 'Audio visualizer lab', exact: true })).toBeVisible()
    await page.reload()
    await page.screenshot({ path: info.outputPath('visualizer-return.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const back = page.getByRole('link', { name: /Coding playground|Return to coding workspace/ })
    await back.focus()
    await expect(back).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('combobox', { name: 'Workspace', exact: true })).toHaveValue('complete')
    await expect(page.getByRole('textbox', { name: /Python code/ })).toHaveValue('print("my experiment")')
    expect(writes).toEqual([])
  })
}

test('unavailable origin offers a local playground fallback', async ({ page }) => {
  await page.goto('/playground/visualizer?workspace=https%3A%2F%2Fexample.com')
  await expect(page.getByRole('status').filter({ hasText: 'linked coding workspace is unavailable' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Coding playground', exact: false })).toHaveAttribute('href', '/playground')
  await expect(page.getByRole('button', { name: 'Start demo', exact: true })).toBeEnabled()
})
